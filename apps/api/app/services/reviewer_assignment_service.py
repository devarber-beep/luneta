"""Admin management of reviewer portfolios."""
from __future__ import annotations

from fastapi import HTTPException, status

from app.domain.enums import AuditActionType, AuditSubjectType, UserRole
from app.models.user import UserModel
from app.repositories.reviewer_assignments import ReviewerAssignmentsRepository
from app.repositories.users import UsersRepository
from app.services.audit_service import AuditService


class ReviewerAssignmentService:
    def __init__(
        self,
        *,
        users_repo: UsersRepository,
        assignments_repo: ReviewerAssignmentsRepository,
        audit_service: AuditService | None = None,
    ) -> None:
        self._users_repo = users_repo
        self._assignments_repo = assignments_repo
        self._audit = audit_service

    async def _require_reviewer(self, reviewer_user_id: str) -> UserModel:
        user = await self._users_repo.get_by_id(reviewer_user_id)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reviewer not found")
        if UserRole(user.role) != UserRole.REVIEWER:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User is not a reviewer")
        return user

    async def _require_investigator(self, investigator_user_id: str) -> UserModel:
        user = await self._users_repo.get_by_id(investigator_user_id)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Investigator not found")
        if UserRole(user.role) not in (UserRole.INVESTIGATOR, UserRole.REVIEWER):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User must be an investigator or reviewer",
            )
        return user

    async def list_investigator_ids(self, *, reviewer_user_id: str) -> list[str]:
        await self._require_reviewer(reviewer_user_id)
        return await self._assignments_repo.list_investigator_ids_for_reviewer(reviewer_user_id)

    async def assign(
        self,
        *,
        actor: UserModel,
        reviewer_user_id: str,
        investigator_user_id: str,
    ) -> None:
        await self._require_reviewer(reviewer_user_id)
        await self._require_investigator(investigator_user_id)
        if reviewer_user_id == investigator_user_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot assign reviewer to self")
        already = await self._assignments_repo.is_assigned(
            reviewer_user_id=reviewer_user_id,
            investigator_user_id=investigator_user_id,
        )
        if already:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Assignment already exists")
        await self._assignments_repo.assign(
            reviewer_user_id=reviewer_user_id,
            investigator_user_id=investigator_user_id,
        )
        if self._audit is not None:
            await self._audit.record(
                actor=actor,
                action_type=AuditActionType.REVIEWER_ASSIGNMENT_CREATED,
                subject_type=AuditSubjectType.USER,
                subject_id=reviewer_user_id,
                current={"investigator_user_id": investigator_user_id},
            )

    async def unassign(
        self,
        *,
        actor: UserModel,
        reviewer_user_id: str,
        investigator_user_id: str,
    ) -> None:
        await self._require_reviewer(reviewer_user_id)
        removed = await self._assignments_repo.remove(
            reviewer_user_id=reviewer_user_id,
            investigator_user_id=investigator_user_id,
        )
        if not removed:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")
        if self._audit is not None:
            await self._audit.record(
                actor=actor,
                action_type=AuditActionType.REVIEWER_ASSIGNMENT_REMOVED,
                subject_type=AuditSubjectType.USER,
                subject_id=reviewer_user_id,
                previous={"investigator_user_id": investigator_user_id},
            )
