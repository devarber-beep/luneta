"""Permission and workflow rules for the vertical slice."""
from app.domain.enums import ScenarioState, UserRole


ALLOWED_WORKFLOW_TRANSITIONS: dict[ScenarioState, set[ScenarioState]] = {
    ScenarioState.DRAFT: {ScenarioState.IN_REVIEW},
    ScenarioState.IN_REVIEW: {ScenarioState.APPROVED},
    ScenarioState.APPROVED: {ScenarioState.PUBLISHED},
    ScenarioState.PUBLISHED: set(),
}


def is_valid_transition(from_state: ScenarioState, to_state: ScenarioState) -> bool:
    return to_state in ALLOWED_WORKFLOW_TRANSITIONS[from_state]


def can_edit_draft(*, actor_user_id: str, author_user_id: str, state: ScenarioState) -> bool:
    return actor_user_id == author_user_id and state == ScenarioState.DRAFT


def can_submit_for_review(
    *,
    actor_role: UserRole,
    actor_user_id: str,
    author_user_id: str,
    state: ScenarioState,
) -> bool:
    return (
        actor_role == UserRole.AUTHOR
        and actor_user_id == author_user_id
        and state == ScenarioState.DRAFT
    )


def can_approve(*, actor_role: UserRole, state: ScenarioState) -> bool:
    return actor_role == UserRole.REVIEWER and state == ScenarioState.IN_REVIEW


def can_publish(*, actor_role: UserRole, state: ScenarioState) -> bool:
    return actor_role == UserRole.REVIEWER and state == ScenarioState.APPROVED


def is_publicly_visible(state: ScenarioState) -> bool:
    return state == ScenarioState.PUBLISHED
