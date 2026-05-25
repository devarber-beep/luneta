"""Authorization for viewing and creating change suggestions."""
from __future__ import annotations

from app.core.permissions import get_collaborator_role
from app.core.reviewer_portfolio import reviewer_has_investigator_in_portfolio
from app.core.rbac_policy import permissions_for_user, user_has_permission
from app.domain.authz_permissions import Permission
from app.domain.enums import CollaboratorRole, ScenarioState, UserRole
from app.models.scenario import ScenarioModel
from app.models.user import UserModel


def _is_owner(*, scenario: ScenarioModel, user_id: str) -> bool:
    return get_collaborator_role(scenario=scenario, user_id=user_id) == CollaboratorRole.OWNER


def _author_in_reviewer_portfolio(
    *,
    user: UserModel,
    scenario: ScenarioModel,
    portfolio_investigator_ids: frozenset[str],
) -> bool:
    return reviewer_has_investigator_in_portfolio(
        user=user,
        investigator_user_id=scenario.author_user_id,
        portfolio_investigator_ids=portfolio_investigator_ids,
    )


def can_list_suggestions(
    *,
    user: UserModel,
    scenario: ScenarioModel,
    has_authored_suggestion: bool = False,
    portfolio_investigator_ids: frozenset[str] | None = None,
    reviewer_has_reviewed_scenario: bool = False,
) -> bool:
    """Owner, admin, collaborator, portfolio reviewers, suggesters, and reviewers who reviewed."""
    if scenario.deleted_at is not None:
        return False
    if not user_has_permission(user=user, permission=Permission.SCENARIO_SUGGESTION_READ):
        return False
    uid = user.id or ""
    portfolio = portfolio_investigator_ids if portfolio_investigator_ids is not None else frozenset()
    role = UserRole(user.role)
    if _is_owner(scenario=scenario, user_id=uid):
        return True
    if get_collaborator_role(scenario=scenario, user_id=uid) == CollaboratorRole.COLLABORATOR:
        return True
    if role == UserRole.ADMIN:
        return True
    if role == UserRole.REVIEWER:
        if _author_in_reviewer_portfolio(
            user=user,
            scenario=scenario,
            portfolio_investigator_ids=portfolio,
        ):
            return True
        if reviewer_has_reviewed_scenario:
            return True
    if has_authored_suggestion and role == UserRole.INVESTIGATOR:
        return True
    return False


def can_read_description_paragraphs(
    *,
    user: UserModel,
    scenario: ScenarioModel,
    portfolio_investigator_ids: frozenset[str],
    reviewer_has_reviewed_scenario: bool = False,
) -> bool:
    """Paragraph text for composing or reviewing suggestions."""
    if scenario.deleted_at is not None:
        return False
    return can_list_suggestions(
        user=user,
        scenario=scenario,
        portfolio_investigator_ids=portfolio_investigator_ids,
        reviewer_has_reviewed_scenario=reviewer_has_reviewed_scenario,
    ) or can_create_suggestion(
        user=user,
        scenario=scenario,
        portfolio_investigator_ids=portfolio_investigator_ids,
        reviewer_has_reviewed_scenario=reviewer_has_reviewed_scenario,
    )


def can_create_suggestion(
    *,
    user: UserModel,
    scenario: ScenarioModel,
    portfolio_investigator_ids: frozenset[str],
    reviewer_has_reviewed_scenario: bool = False,
) -> bool:
    if scenario.deleted_at is not None:
        return False
    if not user_has_permission(user=user, permission=Permission.SCENARIO_SUGGESTION_CREATE):
        return False
    uid = user.id or ""
    if _is_owner(scenario=scenario, user_id=uid):
        return False
    role = UserRole(user.role)
    if role == UserRole.ADMIN:
        if scenario.state in {ScenarioState.IN_REVIEW, ScenarioState.QUEUED}:
            return True
        if scenario.state == ScenarioState.PUBLISHED:
            return True
        return False
    if role == UserRole.REVIEWER:
        if scenario.state in {ScenarioState.IN_REVIEW, ScenarioState.QUEUED}:
            return True
        if scenario.state == ScenarioState.PUBLISHED:
            return not reviewer_has_reviewed_scenario
        return False
    if role == UserRole.INVESTIGATOR:
        return scenario.state == ScenarioState.PUBLISHED
    return False


def can_read_review_feedback_status(
    *,
    user: UserModel,
    scenario: ScenarioModel,
    portfolio_investigator_ids: frozenset[str],
) -> bool:
    """Whether the current user may know if they already left review feedback on this scenario."""
    if scenario.deleted_at is not None:
        return False
    if not user_has_permission(user=user, permission=Permission.SCENARIO_SUGGESTION_CREATE):
        return False
    uid = user.id or ""
    if _is_owner(scenario=scenario, user_id=uid):
        return False
    role = UserRole(user.role)
    if role not in {UserRole.REVIEWER, UserRole.ADMIN}:
        return False
    if scenario.state not in {ScenarioState.IN_REVIEW, ScenarioState.CHANGES_REQUIRED}:
        return False
    if role == UserRole.ADMIN:
        return True
    return _author_in_reviewer_portfolio(
        user=user,
        scenario=scenario,
        portfolio_investigator_ids=portfolio_investigator_ids,
    )


def can_see_suggestion_author_identity(*, user: UserModel) -> bool:
    """Suggestion authorship is visible to administrators only."""
    return UserRole(user.role) == UserRole.ADMIN


def can_resolve_suggestion(*, user: UserModel, scenario: ScenarioModel) -> bool:
    if scenario.deleted_at is not None:
        return False
    if Permission.SCENARIO_UPDATE_OWN not in permissions_for_user(user=user):
        return False
    return _is_owner(scenario=scenario, user_id=user.id or "")
