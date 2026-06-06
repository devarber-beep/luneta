"""Authentication routes for vertical slice."""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db import get_db
from app.deps.authz import require_permission, require_profile_editable
from app.deps.storage import get_user_avatar_storage
from app.domain.authz_permissions import Permission
from app.models.user import UserModel
from app.repositories.email_verification_tokens import EmailVerificationTokensRepository
from app.repositories.scenarios import ScenariosRepository
from app.repositories.users import UsersRepository
from app.dev_email_verification_snapshot import get_last, record_last
from app.schemas.auth import (
    ChangePasswordRequest,
    DevLastEmailVerificationResponse,
    LoginRequest,
    LoginResponse,
    MeResponse,
    ProfilePatchRequest,
    SignupRequest,
    SignupResponse,
    VerifyEmailRequest,
    VerifyEmailResponse,
)
from app.presenters.me_response import build_me_response
from app.services.auth_service import AuthService
from app.services.email_verification_service import EmailVerificationService
from app.services.mailer_service import MailerService
from app.services.notifications_factory import build_notification_service
from app.settings import settings
from app.storage.minio_storage import MinioUserAvatarStorage

router = APIRouter()

_MAX_AVATAR_BYTES = 2 * 1024 * 1024
_ALLOWED_AVATAR_TYPES = frozenset({"image/jpeg", "image/png", "image/webp"})


@router.post("/signup", response_model=SignupResponse)
async def signup(payload: SignupRequest, db: AsyncIOMotorDatabase = Depends(get_db)) -> SignupResponse:
    users_repo = UsersRepository(db)
    tokens_repo = EmailVerificationTokensRepository(db)
    await users_repo.ensure_indexes()
    await tokens_repo.ensure_indexes()

    auth_service = AuthService(
        users_repo=users_repo,
        token_secret=settings.auth_token_secret,
        token_ttl_seconds=settings.auth_token_ttl_seconds,
    )
    email_verification_service = EmailVerificationService(
        tokens_repo=tokens_repo,
        users_repo=users_repo,
        token_ttl_minutes=settings.email_verification_token_ttl_minutes,
    )
    mailer_service = MailerService()

    user = await auth_service.signup(
        email=payload.email,
        password=payload.password,
        nickname=payload.nickname,
    )
    verification_token = await email_verification_service.issue_token(
        user_id=user.id or "", email=str(user.email_normalized)
    )
    if settings.dev_expose_last_email_verification_token:
        record_last(email=str(user.email_normalized), token=verification_token)
    await mailer_service.send_verification_email(to_email=str(user.email_normalized), token=verification_token)
    return SignupResponse(user_id=user.id or "", requires_email_verification=True)


@router.get("/dev/last-email-verification", response_model=DevLastEmailVerificationResponse)
async def dev_last_email_verification() -> DevLastEmailVerificationResponse:
    if not settings.dev_expose_last_email_verification_token:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    snap = get_last()
    if snap is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No verification token recorded yet")
    return DevLastEmailVerificationResponse(email=snap.email, token=snap.token, issued_at=snap.issued_at)


@router.post("/verify-email", response_model=VerifyEmailResponse)
async def verify_email(
    payload: VerifyEmailRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> VerifyEmailResponse:
    users_repo = UsersRepository(db)
    tokens_repo = EmailVerificationTokensRepository(db)
    email_verification_service = EmailVerificationService(
        tokens_repo=tokens_repo,
        users_repo=users_repo,
        token_ttl_minutes=settings.email_verification_token_ttl_minutes,
    )
    verified_email = await email_verification_service.verify(token=payload.token)
    if not verified_email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token")
    await MailerService().send_email_verified_confirmation(to_email=verified_email)
    return VerifyEmailResponse(verified=True)


@router.post("/login", response_model=LoginResponse)
async def login(payload: LoginRequest, db: AsyncIOMotorDatabase = Depends(get_db)) -> LoginResponse:
    users_repo = UsersRepository(db)
    auth_service = AuthService(
        users_repo=users_repo,
        token_secret=settings.auth_token_secret,
        token_ttl_seconds=settings.auth_token_ttl_seconds,
    )
    result = await auth_service.login(email=payload.email, password=payload.password)
    return LoginResponse(
        access_token=result.access_token,
        must_change_password=result.must_change_password,
    )


@router.get("/me", response_model=MeResponse)
async def me(
    user: UserModel = Depends(require_permission(Permission.USER_READ_SELF)),
    storage: MinioUserAvatarStorage = Depends(get_user_avatar_storage),
) -> MeResponse:
    return build_me_response(user=user, storage=storage)


@router.patch("/me", response_model=MeResponse)
async def patch_me(
    payload: ProfilePatchRequest,
    user: UserModel = Depends(require_profile_editable()),
    db: AsyncIOMotorDatabase = Depends(get_db),
    storage: MinioUserAvatarStorage = Depends(get_user_avatar_storage),
) -> MeResponse:
    auth_service = AuthService(
        users_repo=UsersRepository(db),
        token_secret=settings.auth_token_secret,
        token_ttl_seconds=settings.auth_token_ttl_seconds,
        scenarios_repo=ScenariosRepository(db),
    )
    updated = await auth_service.update_profile(user=user, patch=payload)
    return build_me_response(user=updated, storage=storage)


@router.post("/me/avatar", response_model=MeResponse)
async def upload_my_avatar(
    file: UploadFile = File(...),
    user: UserModel = Depends(require_profile_editable()),
    db: AsyncIOMotorDatabase = Depends(get_db),
    storage: MinioUserAvatarStorage = Depends(get_user_avatar_storage),
) -> MeResponse:
    content_type = (file.content_type or "").split(";")[0].strip().lower()
    if content_type not in _ALLOWED_AVATAR_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Avatar must be JPEG, PNG, or WebP",
        )
    raw = await file.read()
    if len(raw) > _MAX_AVATAR_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Avatar too large")
    auth_service = AuthService(
        users_repo=UsersRepository(db),
        token_secret=settings.auth_token_secret,
        token_ttl_seconds=settings.auth_token_ttl_seconds,
    )
    updated = await auth_service.upload_avatar(
        user=user,
        content=raw,
        content_type=content_type,
        storage=storage,
    )
    return build_me_response(user=updated, storage=storage)


@router.delete("/me/avatar", response_model=MeResponse)
async def delete_my_avatar(
    user: UserModel = Depends(require_profile_editable()),
    db: AsyncIOMotorDatabase = Depends(get_db),
    storage: MinioUserAvatarStorage = Depends(get_user_avatar_storage),
) -> MeResponse:
    auth_service = AuthService(
        users_repo=UsersRepository(db),
        token_secret=settings.auth_token_secret,
        token_ttl_seconds=settings.auth_token_ttl_seconds,
    )
    updated = await auth_service.remove_avatar(user=user, storage=storage)
    return build_me_response(user=updated, storage=storage)


@router.post("/me/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    payload: ChangePasswordRequest,
    user: UserModel = Depends(require_permission(Permission.USER_CHANGE_OWN_PASSWORD)),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> None:
    auth_service = AuthService(
        users_repo=UsersRepository(db),
        token_secret=settings.auth_token_secret,
        token_ttl_seconds=settings.auth_token_ttl_seconds,
    )
    await auth_service.change_password(
        user=user,
        current_password=payload.current_password,
        new_password=payload.new_password,
    )
    await build_notification_service(db).notify_password_changed(user=user)
