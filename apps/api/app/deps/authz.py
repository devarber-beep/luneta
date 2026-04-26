"""FastAPI dependencies for permission checks (RBAC layer)."""
from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, HTTPException, status

from app.api_auth import get_current_user
from app.core.rbac_policy import permissions_for_user
from app.domain.authz_permissions import Permission
from app.models.user import UserModel


def require_permission(permission: Permission) -> Callable[..., UserModel]:
    async def _dep(user: UserModel = Depends(get_current_user)) -> UserModel:
        if permission not in permissions_for_user(user=user):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        return user

    return _dep


def require_any_permission(*permissions: Permission) -> Callable[..., UserModel]:
    perms = frozenset(permissions)

    async def _dep(user: UserModel = Depends(get_current_user)) -> UserModel:
        granted = permissions_for_user(user=user)
        if not (granted & perms):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        return user

    return _dep
