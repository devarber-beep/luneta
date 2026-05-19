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


def require_active_user_with_permission(permission: Permission) -> Callable[..., UserModel]:
    """RBAC plus full session (blocked while ``must_change_password`` is true)."""

    async def _dep(user: UserModel = Depends(require_permission(permission))) -> UserModel:
        if user.must_change_password:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Password change required before using this feature",
            )
        return user

    return _dep


def require_any_active_permission(*permissions: Permission) -> Callable[..., UserModel]:
    async def _dep(user: UserModel = Depends(require_any_permission(*permissions))) -> UserModel:
        if user.must_change_password:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Password change required before using this feature",
            )
        return user

    return _dep


def require_profile_editable() -> Callable[..., UserModel]:
    """Profile and avatar updates are not allowed until mandatory password change is done."""

    async def _dep(user: UserModel = Depends(require_permission(Permission.USER_UPDATE_SELF))) -> UserModel:
        if user.must_change_password:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Password change required before updating your profile",
            )
        return user

    return _dep
