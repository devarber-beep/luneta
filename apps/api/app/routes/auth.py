"""Authentication routes for vertical slice."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.api_auth import get_current_user
from app.db import get_db
from app.repositories.email_verification_tokens import EmailVerificationTokensRepository
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
from app.services.auth_service import AuthService
from app.services.email_verification_service import EmailVerificationService
from app.services.mailer_service import MailerService
from app.settings import settings

router = APIRouter()


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
        role=payload.role,
        nickname=payload.nickname,
    )
    verification_token = await email_verification_service.issue_token(user_id=user.id or "", email=user.email)
    if settings.dev_expose_last_email_verification_token:
        record_last(email=user.email, token=verification_token)
    await mailer_service.send_verification_email(to_email=user.email, token=verification_token)
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
    token = await auth_service.login(email=payload.email, password=payload.password)
    return LoginResponse(access_token=token)


@router.get("/me", response_model=MeResponse)
async def me(user=Depends(get_current_user)) -> MeResponse:
    return MeResponse(
        user_id=user.id or "",
        email=user.email,
        role=user.role,
        is_email_verified=user.is_email_verified,
        email_verified_at=user.email_verified_at,
        nickname=user.nickname,
        first_name=user.first_name,
        last_name=user.last_name,
        avatar=user.avatar.model_dump() if user.avatar is not None else None,
        last_login_at=user.last_login_at,
    )


@router.patch("/me", response_model=MeResponse)
async def patch_me(
    payload: ProfilePatchRequest,
    user=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> MeResponse:
    auth_service = AuthService(
        users_repo=UsersRepository(db),
        token_secret=settings.auth_token_secret,
        token_ttl_seconds=settings.auth_token_ttl_seconds,
    )
    updated = await auth_service.update_profile(
        user=user,
        nickname=payload.nickname,
        first_name=payload.first_name,
        last_name=payload.last_name,
    )
    return MeResponse(
        user_id=updated.id or "",
        email=updated.email,
        role=updated.role,
        is_email_verified=updated.is_email_verified,
        email_verified_at=updated.email_verified_at,
        nickname=updated.nickname,
        first_name=updated.first_name,
        last_name=updated.last_name,
        avatar=updated.avatar.model_dump() if updated.avatar is not None else None,
        last_login_at=updated.last_login_at,
    )


@router.post("/me/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    payload: ChangePasswordRequest,
    user=Depends(get_current_user),
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
    await MailerService().send_password_changed_notification(to_email=user.email)
