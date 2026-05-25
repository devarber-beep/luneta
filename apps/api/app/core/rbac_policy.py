"""Central RBAC: role → permissions. Anonymous is a non-persisted actor."""
from __future__ import annotations

from app.domain.authz_permissions import Permission
from app.domain.enums import UserRole
from app.models.user import UserModel

_ANONYMOUS_PERMISSIONS: frozenset[Permission] = frozenset({Permission.SCENARIO_READ_PUBLIC})

_REGISTERED_PERMISSIONS: frozenset[Permission] = _ANONYMOUS_PERMISSIONS | frozenset(
    {
        Permission.SCENARIO_EVALUATE_PUBLISHED,
        Permission.USER_READ_SELF,
        Permission.USER_UPDATE_SELF,
        Permission.USER_CHANGE_OWN_PASSWORD,
    }
)

_INVESTIGATOR_PERMISSIONS: frozenset[Permission] = frozenset(
    {
        Permission.SCENARIO_CREATE_DRAFT,
        Permission.SCENARIO_READ_PUBLIC,
        Permission.SCENARIO_EVALUATE_PUBLISHED,
        Permission.SCENARIO_READ_OWN,
        Permission.SCENARIO_UPDATE_OWN,
        Permission.SCENARIO_DELETE_OWN,
        Permission.SCENARIO_SUBMIT_REVIEW,
        Permission.SCENARIO_SUGGESTION_CREATE,
        Permission.SCENARIO_SUGGESTION_READ,
        Permission.USER_READ_SELF,
        Permission.USER_UPDATE_SELF,
        Permission.USER_CHANGE_OWN_PASSWORD,
        Permission.AUDIT_EVENT_CREATE,
    }
)

_REVIEWER_PERMISSIONS: frozenset[Permission] = _INVESTIGATOR_PERMISSIONS | frozenset(
    {
        Permission.SCENARIO_READ_REVIEW_QUEUE,
        Permission.SCENARIO_UPDATE_IN_REVIEW,
        Permission.SCENARIO_START_REVIEW,
        Permission.SCENARIO_REQUEST_CHANGES,
        Permission.SCENARIO_MARK_NOT_SUITABLE,
        Permission.SCENARIO_PUBLISH,
    }
)

_ADMIN_ONLY_PERMISSIONS: frozenset[Permission] = frozenset(
    {
        Permission.USER_ADMIN_CREATE_INVESTIGATOR,
        Permission.USER_ADMIN_SET_USER_ROLE,
        Permission.USER_ADMIN_SET_ACCOUNT_STATUS,
        Permission.USER_ADMIN_READ_ANY_PROFILE,
        Permission.USER_ADMIN_UPDATE_ANY_PROFILE,
        Permission.USER_ADMIN_MANAGE_REVIEWER_ASSIGNMENTS,
        Permission.USER_ADMIN_MANAGE_SCENARIO_CLASSIFICATION,
        Permission.USER_ADMIN_MANAGE_ETHICAL_RISK_CATALOG,
    }
)

_ADMIN_PERMISSIONS: frozenset[Permission] = _REVIEWER_PERMISSIONS | _ADMIN_ONLY_PERMISSIONS | frozenset(
    {Permission.SCENARIO_REOPEN_NOT_SUITABLE}
)

_ROLE_PERMISSIONS: dict[UserRole, frozenset[Permission]] = {
    UserRole.REGISTERED: _REGISTERED_PERMISSIONS,
    UserRole.INVESTIGATOR: _INVESTIGATOR_PERMISSIONS,
    UserRole.REVIEWER: _REVIEWER_PERMISSIONS,
    UserRole.ADMIN: _ADMIN_PERMISSIONS,
}


def permissions_for_user(*, user: UserModel) -> frozenset[Permission]:
    return _ROLE_PERMISSIONS.get(UserRole(user.role), frozenset())


def permissions_for_anonymous() -> frozenset[Permission]:
    return _ANONYMOUS_PERMISSIONS


def user_has_permission(*, user: UserModel, permission: Permission) -> bool:
    return permission in permissions_for_user(user=user)
