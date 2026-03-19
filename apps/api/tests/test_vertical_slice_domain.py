"""Tests for domain workflow and permissions rules."""
from app.core.permissions import (
    can_approve,
    can_edit_draft,
    can_publish,
    can_submit_for_review,
    is_publicly_visible,
    is_valid_transition,
)
from app.domain.enums import ScenarioState, UserRole


def test_valid_transitions() -> None:
    assert is_valid_transition(ScenarioState.DRAFT, ScenarioState.IN_REVIEW)
    assert is_valid_transition(ScenarioState.IN_REVIEW, ScenarioState.APPROVED)
    assert is_valid_transition(ScenarioState.APPROVED, ScenarioState.PUBLISHED)


def test_invalid_transition_from_published() -> None:
    assert not is_valid_transition(ScenarioState.PUBLISHED, ScenarioState.DRAFT)


def test_author_can_edit_only_own_draft() -> None:
    assert can_edit_draft(
        actor_user_id="u1",
        author_user_id="u1",
        state=ScenarioState.DRAFT,
    )
    assert not can_edit_draft(
        actor_user_id="u2",
        author_user_id="u1",
        state=ScenarioState.DRAFT,
    )
    assert not can_edit_draft(
        actor_user_id="u1",
        author_user_id="u1",
        state=ScenarioState.IN_REVIEW,
    )


def test_submit_approve_publish_permissions() -> None:
    assert can_submit_for_review(
        actor_role=UserRole.AUTHOR,
        actor_user_id="u1",
        author_user_id="u1",
        state=ScenarioState.DRAFT,
    )
    assert can_approve(actor_role=UserRole.REVIEWER, state=ScenarioState.IN_REVIEW)
    assert can_publish(actor_role=UserRole.REVIEWER, state=ScenarioState.APPROVED)
    assert not can_approve(actor_role=UserRole.AUTHOR, state=ScenarioState.IN_REVIEW)


def test_public_visibility() -> None:
    assert is_publicly_visible(ScenarioState.PUBLISHED)
    assert not is_publicly_visible(ScenarioState.DRAFT)
