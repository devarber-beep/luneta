"""Authentication service for signup/login/me."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException, status

from app.core.security import build_access_token, hash_password, parse_access_token, verify_password
from app.core.university_text import parse_university_field
from app.core.user_display_name import parse_person_names
from app.domain.enums import UserAccountStatus, UserRole
from app.models.user import UserModel
from app.repositories.scenarios import ScenariosRepository
from app.repositories.users import UsersRepository
from app.schemas.auth import ProfilePatchRequest
from app.storage.minio_storage import MinioUserAvatarStorage


@dataclass(frozen=True)
class LoginResult:
    access_token: str
    must_change_password: bool


class AuthService:
    def __init__(
        self,
        *,
        users_repo: UsersRepository,
        token_secret: str,
        token_ttl_seconds: int,
        scenarios_repo: ScenariosRepository | None = None,
    ) -> None:
        self._users_repo = users_repo
        self._token_secret = token_secret
        self._token_ttl_seconds = token_ttl_seconds
        self._scenarios_repo = scenarios_repo

    async def signup(self, *, email: str, password: str, first_name: str, last_name: str) -> UserModel:
        existing = await self._users_repo.get_by_email(email)
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            )
        try:
            fn, ln, _, _ = parse_person_names(first_name=first_name, last_name=last_name)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        return await self._users_repo.create(
            email=email,
            password_hash=hash_password(password),
            role=UserRole.REGISTERED,
            first_name=fn,
            last_name=ln,
        )

    async def login(self, *, email: str, password: str) -> LoginResult:
        user = await self._users_repo.get_by_email(email)
        if user is None or not verify_password(password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )
        if user.account_status != UserAccountStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is disabled",
            )
        if user.email_verified_at is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Email is not verified",
            )
        await self._users_repo.touch_last_login(user.id or "")
        token = build_access_token(
            user_id=user.id or "",
            secret=self._token_secret,
            ttl_seconds=self._token_ttl_seconds,
        )
        return LoginResult(access_token=token, must_change_password=user.must_change_password)

    async def me(self, *, bearer_token: str) -> UserModel:
        user_id = parse_access_token(token=bearer_token, secret=self._token_secret)
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )
        user = await self._users_repo.get_by_id(user_id)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )
        if user.account_status != UserAccountStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is disabled",
            )
        if user.email_verified_at is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Email is not verified",
            )
        return user

    async def update_profile(self, *, user: UserModel, patch: ProfilePatchRequest) -> UserModel:
        raw = patch.model_dump(exclude_unset=True)
        if not raw:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update",
            )
        updates: dict[str, Any] = {}

        def _optional_text(val: Any) -> Any:
            if val is None:
                return None
            if not isinstance(val, str):
                return val
            s = val.strip()
            return s if s else None

        name_fields_changed = "first_name" in raw or "last_name" in raw
        if name_fields_changed:
            new_first = _optional_text(raw.get("first_name", user.first_name))
            new_last = _optional_text(raw.get("last_name", user.last_name))
            if not new_first or not new_last:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="First and last name are required",
                )
            try:
                fn, ln, display, display_norm = parse_person_names(first_name=new_first, last_name=new_last)
            except ValueError as exc:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
            updates["first_name"] = fn
            updates["last_name"] = ln
            updates["display_name"] = display
            updates["display_name_normalized"] = display_norm

        for key in ("organization", "biography"):
            if key in raw:
                updates[key] = _optional_text(raw[key])
        if "university" in raw:
            display, normalized = parse_university_field(raw["university"])
            updates["university"] = display
            updates["university_normalized"] = normalized

        updated = await self._users_repo.apply_profile_updates(user.id or "", updates)
        if updated is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        if self._scenarios_repo is not None:
            if name_fields_changed:
                await self._scenarios_repo.sync_author_display_name_for_author(
                    author_user_id=user.id or "",
                    author_display_name=updated.display_name,
                    author_display_name_normalized=updated.display_name_normalized,
                )
            if "university" in raw:
                await self._scenarios_repo.sync_author_university_for_author(
                    author_user_id=user.id or "",
                    author_university=updated.university,
                    author_university_normalized=updated.university_normalized,
                )
        return updated

    async def change_password(
        self,
        *,
        user: UserModel,
        current_password: str,
        new_password: str,
    ) -> None:
        if not verify_password(current_password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect",
            )
        updated = await self._users_repo.set_password_hash(
            user.id or "",
            password_hash=hash_password(new_password),
        )
        if updated is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    async def upload_avatar(
        self,
        *,
        user: UserModel,
        content: bytes,
        content_type: str,
        storage: MinioUserAvatarStorage,
    ) -> UserModel:
        storage.ensure_bucket()
        if user.avatar:
            storage.delete_object(object_key=user.avatar.object_key)
        avatar = storage.upload_avatar(user_id=user.id or "", content=content, content_type=content_type)
        updated = await self._users_repo.set_avatar(user.id or "", avatar=avatar.model_dump())
        if updated is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return updated

    async def remove_avatar(self, *, user: UserModel, storage: MinioUserAvatarStorage) -> UserModel:
        if user.avatar:
            storage.delete_object(object_key=user.avatar.object_key)
        updated = await self._users_repo.set_avatar(user.id or "", avatar=None)
        if updated is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return updated
