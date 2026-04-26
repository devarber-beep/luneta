"""Permission and workflow rules for the vertical slice."""
from app.domain.enums import CollaboratorRole, ScenarioState
from app.models.scenario import ScenarioModel


ALLOWED_WORKFLOW_TRANSITIONS: dict[ScenarioState, set[ScenarioState]] = {
    ScenarioState.DRAFT: {ScenarioState.IN_REVIEW},
    ScenarioState.IN_REVIEW: {ScenarioState.APPROVED, ScenarioState.DRAFT},
    ScenarioState.APPROVED: {ScenarioState.PUBLISHED},
    ScenarioState.PUBLISHED: {ScenarioState.IN_REVIEW},
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


def has_republication_pending(*, scenario: ScenarioModel) -> bool:
    """Published scenario with working copy differing from last live public snapshot."""
    if scenario.public_slug is None:
        return False
    return (
        scenario.title != scenario.public_title
        or scenario.body_markdown != scenario.public_body_markdown
        or scenario.slug != scenario.public_slug
    )


def can_submit_for_review(
    *,
    collaborator_role: CollaboratorRole | None,
    state: ScenarioState,
    scenario: ScenarioModel,
) -> bool:
    if collaborator_role != CollaboratorRole.OWNER:
        return False
    if state == ScenarioState.DRAFT:
        return True
    if state == ScenarioState.PUBLISHED:
        return scenario.first_published_at is not None and has_republication_pending(scenario=scenario)
    return False


def can_edit_draft(*, collaborator_role: CollaboratorRole | None, state: ScenarioState) -> bool:
    return collaborator_role in {CollaboratorRole.OWNER, CollaboratorRole.EDITOR} and state == ScenarioState.DRAFT


def can_edit_published_content(*, collaborator_role: CollaboratorRole | None) -> bool:
    """Only the scenario owner (author) may edit content after publish."""
    return collaborator_role == CollaboratorRole.OWNER


def can_manage_collaborators(*, collaborator_role: CollaboratorRole | None) -> bool:
    return collaborator_role == CollaboratorRole.OWNER


def is_publicly_visible(state: ScenarioState) -> bool:
    return state == ScenarioState.PUBLISHED


