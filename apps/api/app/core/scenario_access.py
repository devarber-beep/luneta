"""Contextual authorization rules for scenarios (resource + state + ownership)."""
from __future__ import annotations

from app.core.permissions import (
    can_edit_draft,
    can_edit_published_content,
    can_start_applying_changes,
    can_submit_for_review as _can_submit_for_review_state,
    get_collaborator_role,
    is_review_pipeline_state,
)
from app.core.reviewer_portfolio import reviewer_has_investigator_in_portfolio
from app.core.rbac_policy import permissions_for_user
from app.domain.authz_permissions import Permission
from app.domain.enums import ScenarioState, UserRole
from app.models.scenario import ScenarioModel
from app.models.user import UserModel


def _is_participant(*, scenario: ScenarioModel, user_id: str) -> bool:
    return get_collaborator_role(scenario=scenario, user_id=user_id) is not None


def _reviewer_portfolio_ok(
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


def can_read_scenario(
    *,
    user: UserModel,
    scenario: ScenarioModel,
    portfolio_investigator_ids: frozenset[str] | None = None,
) -> bool:
    if scenario.deleted_at is not None:
        return False
    uid = user.id or ""
    role = UserRole(user.role)
    granted = permissions_for_user(user=user)

    from app.core.permissions import is_publicly_visible

    if is_publicly_visible(scenario=scenario) and Permission.SCENARIO_READ_PUBLIC in granted:
        return True
    if _is_participant(scenario=scenario, user_id=uid):
        return True
    if role in (UserRole.REVIEWER, UserRole.ADMIN) and Permission.SCENARIO_READ_REVIEW_QUEUE in granted:
        portfolio = portfolio_investigator_ids if portfolio_investigator_ids is not None else frozenset()
        if is_review_pipeline_state(scenario.state):
            if role == UserRole.ADMIN:
                return True
            return _reviewer_portfolio_ok(
                user=user, scenario=scenario, portfolio_investigator_ids=portfolio
            )
        if scenario.state in {ScenarioState.CHANGES_REQUIRED, ScenarioState.NOT_SUITABLE}:
            if role == UserRole.ADMIN:
                return True
            return _reviewer_portfolio_ok(
                user=user, scenario=scenario, portfolio_investigator_ids=portfolio
            )
    return False


def can_update_scenario(
    *,
    user: UserModel,
    scenario: ScenarioModel,
    portfolio_investigator_ids: frozenset[str] | None = None,
) -> bool:
    if scenario.deleted_at is not None:
        return False
    if scenario.state == ScenarioState.NOT_SUITABLE:
        return False
    uid = user.id or ""
    granted = permissions_for_user(user=user)
    collaborator = get_collaborator_role(scenario=scenario, user_id=uid)

    if scenario.state == ScenarioState.IN_REVIEW:
        if Permission.SCENARIO_UPDATE_IN_REVIEW not in granted:
            return False
        portfolio = portfolio_investigator_ids if portfolio_investigator_ids is not None else frozenset()
        return _reviewer_portfolio_ok(
            user=user, scenario=scenario, portfolio_investigator_ids=portfolio
        )
    if scenario.state in {ScenarioState.DRAFT, ScenarioState.APPLYING_CHANGES}:
        return Permission.SCENARIO_UPDATE_OWN in granted and can_edit_draft(
            collaborator_role=collaborator,
            state=scenario.state,
        )
    if scenario.state == ScenarioState.PUBLISHED:
        return Permission.SCENARIO_UPDATE_OWN in granted and can_edit_published_content(collaborator_role=collaborator)
    return False


def can_submit_review(*, user: UserModel, scenario: ScenarioModel) -> bool:
    if scenario.deleted_at is not None:
        return False
    if Permission.SCENARIO_SUBMIT_REVIEW not in permissions_for_user(user=user):
        return False
    uid = user.id or ""
    collaborator = get_collaborator_role(scenario=scenario, user_id=uid)
    return _can_submit_for_review_state(
        collaborator_role=collaborator,
        state=scenario.state,
        scenario=scenario,
    )


def can_start_applying_changes_scenario(*, user: UserModel, scenario: ScenarioModel) -> bool:
    if scenario.deleted_at is not None:
        return False
    if Permission.SCENARIO_SUBMIT_REVIEW not in permissions_for_user(user=user):
        return False
    uid = user.id or ""
    collaborator = get_collaborator_role(scenario=scenario, user_id=uid)
    return can_start_applying_changes(collaborator_role=collaborator, state=scenario.state)


def _not_own_scenario(*, user: UserModel, scenario: ScenarioModel) -> bool:
    return (user.id or "") != scenario.author_user_id


def _reviewer_action_on_in_review(
    *,
    user: UserModel,
    scenario: ScenarioModel,
    portfolio_investigator_ids: frozenset[str],
) -> bool:
    if scenario.state != ScenarioState.IN_REVIEW:
        return False
    if UserRole(user.role) == UserRole.ADMIN:
        return True
    if not _not_own_scenario(user=user, scenario=scenario):
        return False
    return _reviewer_portfolio_ok(
        user=user, scenario=scenario, portfolio_investigator_ids=portfolio_investigator_ids
    )


def can_start_review_scenario(
    *,
    user: UserModel,
    scenario: ScenarioModel,
    portfolio_investigator_ids: frozenset[str] | None = None,
) -> bool:
    if scenario.deleted_at is not None:
        return False
    if Permission.SCENARIO_START_REVIEW not in permissions_for_user(user=user):
        return False
    if scenario.state != ScenarioState.QUEUED:
        return False
    portfolio = portfolio_investigator_ids if portfolio_investigator_ids is not None else frozenset()
    if UserRole(user.role) == UserRole.ADMIN:
        return True
    if not _not_own_scenario(user=user, scenario=scenario):
        return False
    return _reviewer_portfolio_ok(
        user=user, scenario=scenario, portfolio_investigator_ids=portfolio
    )


def can_publish_scenario(
    *,
    user: UserModel,
    scenario: ScenarioModel,
    portfolio_investigator_ids: frozenset[str] | None = None,
) -> bool:
    if scenario.deleted_at is not None:
        return False
    if Permission.SCENARIO_PUBLISH not in permissions_for_user(user=user):
        return False
    portfolio = portfolio_investigator_ids if portfolio_investigator_ids is not None else frozenset()
    return _reviewer_action_on_in_review(user=user, scenario=scenario, portfolio_investigator_ids=portfolio)


def can_request_changes_scenario(
    *,
    user: UserModel,
    scenario: ScenarioModel,
    portfolio_investigator_ids: frozenset[str] | None = None,
) -> bool:
    if scenario.deleted_at is not None:
        return False
    if Permission.SCENARIO_REQUEST_CHANGES not in permissions_for_user(user=user):
        return False
    portfolio = portfolio_investigator_ids if portfolio_investigator_ids is not None else frozenset()
    return _reviewer_action_on_in_review(user=user, scenario=scenario, portfolio_investigator_ids=portfolio)


def can_mark_not_suitable_scenario(
    *,
    user: UserModel,
    scenario: ScenarioModel,
    portfolio_investigator_ids: frozenset[str] | None = None,
) -> bool:
    if scenario.deleted_at is not None:
        return False
    if Permission.SCENARIO_MARK_NOT_SUITABLE not in permissions_for_user(user=user):
        return False
    portfolio = portfolio_investigator_ids if portfolio_investigator_ids is not None else frozenset()
    return _reviewer_action_on_in_review(user=user, scenario=scenario, portfolio_investigator_ids=portfolio)


def can_reopen_not_suitable(*, user: UserModel, scenario: ScenarioModel) -> bool:
    if scenario.deleted_at is not None:
        return False
    if Permission.SCENARIO_REOPEN_NOT_SUITABLE not in permissions_for_user(user=user):
        return False
    return scenario.state == ScenarioState.NOT_SUITABLE


def can_delete_own_draft(*, user: UserModel, scenario: ScenarioModel) -> bool:
    if scenario.deleted_at is not None:
        return False
    if Permission.SCENARIO_DELETE_OWN not in permissions_for_user(user=user):
        return False
    if scenario.state != ScenarioState.DRAFT:
        return False
    return (user.id or "") == scenario.author_user_id
