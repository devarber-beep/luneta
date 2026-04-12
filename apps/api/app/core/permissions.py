"""Permission and workflow rules for the vertical slice."""
from app.domain.enums import CollaboratorRole, ScenarioState, UserRole
from app.models.scenario import ScenarioModel


ALLOWED_WORKFLOW_TRANSITIONS: dict[ScenarioState, set[ScenarioState]] = {
    ScenarioState.DRAFT: {ScenarioState.IN_REVIEW},
    ScenarioState.IN_REVIEW: {ScenarioState.APPROVED},
    ScenarioState.APPROVED: {ScenarioState.PUBLISHED},
    ScenarioState.PUBLISHED: set(),
}


def is_valid_transition(from_state: ScenarioState, to_state: ScenarioState) -> bool:
    return to_state in ALLOWED_WORKFLOW_TRANSITIONS[from_state]


def get_collaborator_role(*, scenario: ScenarioModel, actor_user_id: str) -> CollaboratorRole | None:
    for collaborator in scenario.collaborators:
        if collaborator.user_id == actor_user_id:
            return collaborator.role
    if actor_user_id == scenario.author_user_id:
        return CollaboratorRole.OWNER
    return None


def can_submit_for_review(
    *,
    actor_role: UserRole,
    collaborator_role: CollaboratorRole | None,
    state: ScenarioState,
) -> bool:
    return actor_role == UserRole.AUTHOR and collaborator_role == CollaboratorRole.OWNER and state == ScenarioState.DRAFT


def can_edit_draft(*, collaborator_role: CollaboratorRole | None, state: ScenarioState) -> bool:
    return collaborator_role in {CollaboratorRole.OWNER, CollaboratorRole.EDITOR} and state == ScenarioState.DRAFT


def can_manage_collaborators(*, collaborator_role: CollaboratorRole | None) -> bool:
    return collaborator_role == CollaboratorRole.OWNER


def has_scenario_read_access(*, actor_role: UserRole, collaborator_role: CollaboratorRole | None) -> bool:
    return actor_role == UserRole.REVIEWER or collaborator_role is not None


def can_approve(*, actor_role: UserRole, state: ScenarioState) -> bool:
    return actor_role == UserRole.REVIEWER and state == ScenarioState.IN_REVIEW


def can_publish(*, actor_role: UserRole, state: ScenarioState) -> bool:
    return actor_role == UserRole.REVIEWER and state == ScenarioState.APPROVED


def is_publicly_visible(state: ScenarioState) -> bool:
    return state == ScenarioState.PUBLISHED


def can_view_comments(*, scenario: ScenarioModel, actor_role: UserRole | None, collaborator_role: CollaboratorRole | None) -> bool:
    if scenario.state == ScenarioState.PUBLISHED:
        return True
    if actor_role is None:
        return False
    return has_scenario_read_access(actor_role=actor_role, collaborator_role=collaborator_role)


def can_add_comment(
    *,
    scenario: ScenarioModel,
    actor_role: UserRole,
    collaborator_role: CollaboratorRole | None,
) -> bool:
    if scenario.state == ScenarioState.PUBLISHED:
        return actor_role in {UserRole.AUTHOR, UserRole.REVIEWER}
    return has_scenario_read_access(actor_role=actor_role, collaborator_role=collaborator_role)
