"""Central RBAC: role → permissions. Anonymous is a non-persisted actor."""
from __future__ import annotations

from app.domain.authz_permissions import Permission
from app.domain.enums import UserRole
from app.models.user import UserModel

_ANONYMOUS_PERMISSIONS: frozenset[Permission] = frozenset({Permission.SCENARIO_READ_PUBLIC})

_INVESTIGATOR_PERMISSIONS: frozenset[Permission] = frozenset(
    {
        Permission.SCENARIO_CREATE_DRAFT,
        Permission.SCENARIO_READ_PUBLIC,
        Permission.SCENARIO_READ_OWN,
        Permission.SCENARIO_UPDATE_OWN,
        Permission.SCENARIO_DELETE_OWN,
        Permission.SCENARIO_SUBMIT_REVIEW,
        Permission.USER_READ_SELF,
        Permission.USER_UPDATE_SELF,
        Permission.AUDIT_EVENT_CREATE,
    }
)

_COORDINATOR_PERMISSIONS: frozenset[Permission] = _INVESTIGATOR_PERMISSIONS | frozenset(
    {
        Permission.SCENARIO_READ_REVIEW_QUEUE,
        Permission.SCENARIO_UPDATE_IN_REVIEW,
        Permission.SCENARIO_REJECT,
        Permission.SCENARIO_PUBLISH,
    }
)

_ROLE_PERMISSIONS: dict[UserRole, frozenset[Permission]] = {
    UserRole.INVESTIGATOR: _INVESTIGATOR_PERMISSIONS,
    UserRole.COORDINATOR: _COORDINATOR_PERMISSIONS,
}


def permissions_for_user(*, user: UserModel) -> frozenset[Permission]:
    return _ROLE_PERMISSIONS.get(UserRole(user.role), frozenset())


def permissions_for_anonymous() -> frozenset[Permission]:
    return _ANONYMOUS_PERMISSIONS


def user_has_permission(*, user: UserModel, permission: Permission) -> bool:
    return permission in permissions_for_user(user=user)
