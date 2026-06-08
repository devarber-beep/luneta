"""Authorization for ethical evaluations on published scenarios."""
from __future__ import annotations

from app.core.permissions import get_collaborator_role, is_publicly_visible
from app.core.rbac_policy import user_has_permission
from app.domain.authz_permissions import Permission
from app.domain.enums import CollaboratorRole, UserRole
from app.models.scenario import ScenarioModel
from app.models.user import UserModel


def _is_scenario_owner(*, scenario: ScenarioModel, user_id: str) -> bool:
    return get_collaborator_role(scenario=scenario, user_id=user_id) == CollaboratorRole.OWNER


def can_submit_evaluation(*, user: UserModel, scenario: ScenarioModel) -> bool:
    if scenario.deleted_at is not None:
        return False
    if not user_has_permission(user=user, permission=Permission.SCENARIO_EVALUATE_PUBLISHED):
        return False
    if not is_publicly_visible(scenario=scenario):
        return False
    uid = user.id or ""
    if uid == scenario.author_user_id:
        return False
    return True


def can_read_own_evaluation(*, user: UserModel, scenario: ScenarioModel) -> bool:
    return can_submit_evaluation(user=user, scenario=scenario) or _is_scenario_owner(
        scenario=scenario, user_id=user.id or ""
    )


def can_read_evaluation_summary(*, user: UserModel, scenario: ScenarioModel) -> bool:
    """Aggregate scores and risk labels: owner, admin, or anyone who may evaluate this scenario."""
    if scenario.deleted_at is not None:
        return False
    if not is_publicly_visible(scenario=scenario):
        return False
    if _is_scenario_owner(scenario=scenario, user_id=user.id or ""):
        return True
    if UserRole(user.role) == UserRole.ADMIN:
        return True
    return can_submit_evaluation(user=user, scenario=scenario)


def can_read_evaluation_comments(*, user: UserModel, scenario: ScenarioModel) -> bool:
    """Free-text evaluation comments only; scenario owner, no evaluator identity."""
    if scenario.deleted_at is not None:
        return False
    if not is_publicly_visible(scenario=scenario):
        return False
    return _is_scenario_owner(scenario=scenario, user_id=user.id or "")


def can_read_evaluation_detail(*, user: UserModel, scenario: ScenarioModel) -> bool:
    """Per-evaluation breakdown including scores and evaluator identity; admin only."""
    if scenario.deleted_at is not None:
        return False
    return UserRole(user.role) == UserRole.ADMIN


def can_moderate_evaluations(*, user: UserModel) -> bool:
    return user_has_permission(user=user, permission=Permission.EVALUATION_MODERATE)
