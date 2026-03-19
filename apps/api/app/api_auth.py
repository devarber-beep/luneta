"""Shared auth dependency helpers for authenticated routes."""
from __future__ import annotations

from fastapi import Depends, Header, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db import get_db
from app.repositories.users import UsersRepository
from app.services.auth_service import AuthService
from app.settings import settings


def parse_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing authorization")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authorization scheme")
    return token


async def get_current_user(
    authorization: str | None = Header(default=None),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    token = parse_bearer_token(authorization)
    users_repo = UsersRepository(db)
    auth_service = AuthService(
        users_repo=users_repo,
        token_secret=settings.auth_token_secret,
        token_ttl_seconds=settings.auth_token_ttl_seconds,
    )
    return await auth_service.me(bearer_token=token)
