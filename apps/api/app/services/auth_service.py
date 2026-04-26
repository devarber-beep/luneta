"""Authentication service for signup/login/me."""
from __future__ import annotations

from fastapi import HTTPException, status

from app.core.security import build_access_token, hash_password, parse_access_token, verify_password
from app.models.user import UserModel
from app.repositories.users import UsersRepository


class AuthService:
    def __init__(
        self,
        *,
        users_repo: UsersRepository,
        token_secret: str,
        token_ttl_seconds: int,
    ) -> None:
        self._users_repo = users_repo
        self._token_secret = token_secret
        self._token_ttl_seconds = token_ttl_seconds

    async def signup(self, *, email: str, password: str, role: str, nickname: str) -> UserModel:
        existing = await self._users_repo.get_by_email(email)
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            )
        nick = nickname.strip()
        existing_nick = await self._users_repo.get_by_nickname(nick)
        if existing_nick is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Nickname already registered",
            )
        return await self._users_repo.create(
            email=email,
            password_hash=hash_password(password),
            role=role,
            nickname=nick,
        )

    async def login(self, *, email: str, password: str) -> str:
        user = await self._users_repo.get_by_email(email)
        if user is None or not verify_password(password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )
        if not user.is_email_verified:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Email is not verified",
            )
        await self._users_repo.touch_last_login(user.id or "")
        return build_access_token(
            user_id=user.id or "",
            secret=self._token_secret,
            ttl_seconds=self._token_ttl_seconds,
        )

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
        if not user.is_email_verified:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Email is not verified",
            )
        return user

    async def update_profile(
        self,
        *,
        user: UserModel,
        nickname: str,
        first_name: str | None,
        last_name: str | None,
    ) -> UserModel:
        nick = nickname.strip()
        if len(nick) < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nickname must have at least 2 characters",
            )
        other = await self._users_repo.get_by_nickname(nick)
        if other is not None and other.id != user.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Nickname already registered",
            )
        fn = user.first_name
        ln = user.last_name
        if first_name is not None:
            fn = first_name.strip() or None
        if last_name is not None:
            ln = last_name.strip() or None

        updated = await self._users_repo.update_profile(
            user.id or "",
            nickname=nick,
            first_name=fn,
            last_name=ln,
        )
        if updated is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
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
