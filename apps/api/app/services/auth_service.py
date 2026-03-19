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

    async def signup(self, *, email: str, password: str, role: str) -> UserModel:
        existing = await self._users_repo.get_by_email(email)
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            )
        return await self._users_repo.create(
            email=email,
            password_hash=hash_password(password),
            role=role,
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
