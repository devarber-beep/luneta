"""Contextual authorization rules for scenarios (resource + state + ownership)."""
from __future__ import annotations

from app.core.permissions import (
    can_edit_draft,
    can_edit_published_content,
    can_submit_for_review as _can_submit_for_review_state,
    get_collaborator_role,
)
from app.core.rbac_policy import permissions_for_user
from app.domain.authz_permissions import Permission
from app.domain.enums import ScenarioState, UserRole
from app.models.scenario import ScenarioModel
from app.models.user import UserModel


def _is_participant(*, scenario: ScenarioModel, user_id: str) -> bool:
    return get_collaborator_role(scenario=scenario, actor_user_id=user_id) is not None


def can_read_scenario(*, user: UserModel, scenario: ScenarioModel) -> bool:
    if scenario.deleted_at is not None:
        return False
    uid = user.id or ""
    role = UserRole(user.role)
    granted = permissions_for_user(user=user)

    if scenario.state == ScenarioState.PUBLISHED and Permission.SCENARIO_READ_PUBLIC in granted:
        return True
    if _is_participant(scenario=scenario, user_id=uid):
        return True
    if role == UserRole.COORDINATOR and Permission.SCENARIO_READ_REVIEW_QUEUE in granted:
        if scenario.state in (ScenarioState.IN_REVIEW, ScenarioState.APPROVED):
            return True
    return False


def can_update_scenario(*, user: UserModel, scenario: ScenarioModel) -> bool:
    if scenario.deleted_at is not None:
        return False
    uid = user.id or ""
    granted = permissions_for_user(user=user)
    collaborator = get_collaborator_role(scenario=scenario, actor_user_id=uid)

    if scenario.state == ScenarioState.IN_REVIEW:
        return Permission.SCENARIO_UPDATE_IN_REVIEW in granted
    if scenario.state == ScenarioState.DRAFT:
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
    collaborator = get_collaborator_role(scenario=scenario, actor_user_id=uid)
    return _can_submit_for_review_state(
        collaborator_role=collaborator,
        state=scenario.state,
        scenario=scenario,
    )


def _not_own_scenario(*, user: UserModel, scenario: ScenarioModel) -> bool:
    return (user.id or "") != scenario.author_user_id


def can_approve_scenario(*, user: UserModel, scenario: ScenarioModel) -> bool:
    if scenario.deleted_at is not None:
        return False
    if Permission.SCENARIO_APPROVE not in permissions_for_user(user=user):
        return False
    if scenario.state != ScenarioState.IN_REVIEW:
        return False
    return _not_own_scenario(user=user, scenario=scenario)


def can_publish_scenario(*, user: UserModel, scenario: ScenarioModel) -> bool:
    if scenario.deleted_at is not None:
        return False
    if Permission.SCENARIO_PUBLISH not in permissions_for_user(user=user):
        return False
    if scenario.state != ScenarioState.APPROVED:
        return False
    return _not_own_scenario(user=user, scenario=scenario)


def can_reject_scenario(*, user: UserModel, scenario: ScenarioModel) -> bool:
    if scenario.deleted_at is not None:
        return False
    if Permission.SCENARIO_REJECT not in permissions_for_user(user=user):
        return False
    if scenario.state != ScenarioState.IN_REVIEW:
        return False
    return _not_own_scenario(user=user, scenario=scenario)


def can_delete_own_draft(*, user: UserModel, scenario: ScenarioModel) -> bool:
    if scenario.deleted_at is not None:
        return False
    if Permission.SCENARIO_DELETE_OWN not in permissions_for_user(user=user):
        return False
    if scenario.state != ScenarioState.DRAFT:
        return False
    return (user.id or "") == scenario.author_user_id
