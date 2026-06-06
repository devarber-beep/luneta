"""Admin routes for user management."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db import get_db
from app.deps.authz import require_permission
from app.deps.storage import get_user_avatar_storage
from app.domain.authz_permissions import Permission
from app.domain.enums import UserAccountStatus, UserRole
from app.models.user import UserModel
from app.presenters.me_response import build_me_response
from app.repositories.audit_events import AuditEventsRepository
from app.repositories.email_verification_tokens import EmailVerificationTokensRepository
from app.repositories.reviewer_assignments import ReviewerAssignmentsRepository
from app.repositories.scenarios import ScenariosRepository
from app.repositories.users import UsersRepository
from app.schemas.admin_users import (
    AdminCreateInvestigatorRequest,
    AdminCreateInvestigatorResponse,
    AdminSetAccountStatusRequest,
    AdminSetUserRoleRequest,
    AdminUserMutationResponse,
    ReviewerInvestigatorIdsResponse,
    AdminUserSummaryResponse,
)
from app.schemas.auth import MeResponse, ProfilePatchRequest
from app.services.admin_user_service import AdminUserService
from app.services.audit_service import AuditService
from app.services.auth_service import AuthService
from app.services.notifications_factory import build_notification_service
from app.services.reviewer_assignment_service import ReviewerAssignmentService
from app.settings import settings
from app.storage.minio_storage import MinioUserAvatarStorage

router = APIRouter()


def _admin_user_service(db: AsyncIOMotorDatabase) -> AdminUserService:
    return AdminUserService(
        users_repo=UsersRepository(db),
        tokens_repo=EmailVerificationTokensRepository(db),
        notification_service=build_notification_service(db),
        email_verification_token_ttl_minutes=settings.email_verification_token_ttl_minutes,
        audit_service=AuditService(audit_repo=AuditEventsRepository(db)),
    )


def _reviewer_assignment_service(db: AsyncIOMotorDatabase) -> ReviewerAssignmentService:
    return ReviewerAssignmentService(
        users_repo=UsersRepository(db),
        assignments_repo=ReviewerAssignmentsRepository(db),
        audit_service=AuditService(audit_repo=AuditEventsRepository(db)),
    )


@router.post(
    "/users/investigators",
    response_model=AdminCreateInvestigatorResponse,
    status_code=status.HTTP_201_CREATED,
)
async def admin_create_investigator(
    payload: AdminCreateInvestigatorRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    actor: UserModel = Depends(require_permission(Permission.USER_ADMIN_CREATE_INVESTIGATOR)),
) -> AdminCreateInvestigatorResponse:
    await UsersRepository(db).ensure_indexes()
    await EmailVerificationTokensRepository(db).ensure_indexes()
    user = await _admin_user_service(db).create_investigator_account(
        actor=actor,
        email=str(payload.email),
        nickname=payload.nickname,
        first_name=payload.first_name,
        last_name=payload.last_name,
    )
    return AdminCreateInvestigatorResponse(user_id=user.id or "", email_normalized=user.email_normalized)


@router.get("/users/{user_id}/profile", response_model=MeResponse)
async def admin_get_user_profile(
    user_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    _: UserModel = Depends(require_permission(Permission.USER_ADMIN_READ_ANY_PROFILE)),
    storage: MinioUserAvatarStorage = Depends(get_user_avatar_storage),
) -> MeResponse:
    user = await UsersRepository(db).get_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return build_me_response(user=user, storage=storage)


@router.patch("/users/{user_id}/profile", response_model=MeResponse)
async def admin_patch_user_profile(
    user_id: str,
    payload: ProfilePatchRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    _: UserModel = Depends(require_permission(Permission.USER_ADMIN_UPDATE_ANY_PROFILE)),
    storage: MinioUserAvatarStorage = Depends(get_user_avatar_storage),
) -> MeResponse:
    users_repo = UsersRepository(db)
    target = await users_repo.get_by_id(user_id)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    auth_service = AuthService(
        users_repo=users_repo,
        token_secret=settings.auth_token_secret,
        token_ttl_seconds=settings.auth_token_ttl_seconds,
        scenarios_repo=ScenariosRepository(db),
    )
    updated = await auth_service.update_profile(user=target, patch=payload)
    return build_me_response(user=updated, storage=storage)


@router.patch("/users/{user_id}/role", response_model=AdminUserMutationResponse)
async def admin_set_user_role(
    user_id: str,
    payload: AdminSetUserRoleRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    actor: UserModel = Depends(require_permission(Permission.USER_ADMIN_SET_USER_ROLE)),
) -> AdminUserMutationResponse:
    user = await _admin_user_service(db).set_user_role(
        actor=actor, target_user_id=user_id, new_role=payload.role
    )
    return AdminUserMutationResponse(
        user_id=user.id or "",
        role=user.role,
        account_status=user.account_status,
    )


@router.patch("/users/{user_id}/account-status", response_model=AdminUserMutationResponse)
async def admin_set_account_status(
    user_id: str,
    payload: AdminSetAccountStatusRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    actor: UserModel = Depends(require_permission(Permission.USER_ADMIN_SET_ACCOUNT_STATUS)),
) -> AdminUserMutationResponse:
    user = await _admin_user_service(db).set_account_status(
        actor=actor,
        target_user_id=user_id,
        account_status=payload.account_status,
    )
    return AdminUserMutationResponse(
        user_id=user.id or "",
        role=user.role,
        account_status=user.account_status,
    )


@router.get("/users/summary", response_model=list[AdminUserSummaryResponse])
async def admin_list_users_summary(
    role: UserRole | None = None,
    db: AsyncIOMotorDatabase = Depends(get_db),
    _: UserModel = Depends(require_permission(Permission.USER_ADMIN_READ_ANY_PROFILE)),
) -> list[AdminUserSummaryResponse]:
    repo = UsersRepository(db)
    roles = [role] if role is not None else [UserRole.REVIEWER, UserRole.INVESTIGATOR]
    users = await repo.list_by_roles(roles)
    return [
        AdminUserSummaryResponse(
            user_id=u.id or "",
            nickname=u.nickname,
            email_normalized=u.email_normalized,
            role=u.role,
        )
        for u in users
        if u.account_status == UserAccountStatus.ACTIVE
    ]


@router.get(
    "/reviewers/{reviewer_id}/investigators",
    response_model=ReviewerInvestigatorIdsResponse,
)
async def admin_list_reviewer_investigators(
    reviewer_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    _: UserModel = Depends(require_permission(Permission.USER_ADMIN_MANAGE_REVIEWER_ASSIGNMENTS)),
) -> ReviewerInvestigatorIdsResponse:
    await ReviewerAssignmentsRepository(db).ensure_indexes()
    ids = await _reviewer_assignment_service(db).list_investigator_ids(reviewer_user_id=reviewer_id)
    return ReviewerInvestigatorIdsResponse(reviewer_user_id=reviewer_id, investigator_user_ids=ids)


@router.put(
    "/reviewers/{reviewer_id}/investigators/{investigator_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def admin_assign_investigator_to_reviewer(
    reviewer_id: str,
    investigator_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    actor: UserModel = Depends(require_permission(Permission.USER_ADMIN_MANAGE_REVIEWER_ASSIGNMENTS)),
) -> None:
    await ReviewerAssignmentsRepository(db).ensure_indexes()
    await _reviewer_assignment_service(db).assign(
        actor=actor,
        reviewer_user_id=reviewer_id,
        investigator_user_id=investigator_id,
    )


@router.delete(
    "/reviewers/{reviewer_id}/investigators/{investigator_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def admin_unassign_investigator_from_reviewer(
    reviewer_id: str,
    investigator_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    actor: UserModel = Depends(require_permission(Permission.USER_ADMIN_MANAGE_REVIEWER_ASSIGNMENTS)),
) -> None:
    await _reviewer_assignment_service(db).unassign(
        actor=actor,
        reviewer_user_id=reviewer_id,
        investigator_user_id=investigator_id,
    )
