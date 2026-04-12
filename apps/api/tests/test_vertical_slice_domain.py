"""Tests for domain workflow and permissions rules."""
from datetime import UTC, datetime

from app.core.permissions import (
    can_add_comment,
    can_approve,
    can_edit_draft,
    can_manage_collaborators,
    can_publish,
    can_submit_for_review,
    can_view_comments,
    get_collaborator_role,
    has_scenario_read_access,
    is_publicly_visible,
    is_valid_transition,
)
from app.domain.enums import CollaboratorRole, ScenarioState, UserRole
from app.models.scenario import ScenarioModel


def _scenario(*, state: ScenarioState) -> ScenarioModel:
    now = datetime.now(UTC)
    return ScenarioModel(
        _id="1",
        slug="s",
        title="t",
        body_markdown="b",
        author_user_id="u1",
        collaborators=[],
        state=state,
        current_revision_number=1,
        published_at=now if state == ScenarioState.PUBLISHED else None,
        created_at=now,
        updated_at=now,
    )


def test_valid_transitions() -> None:
    assert is_valid_transition(ScenarioState.DRAFT, ScenarioState.IN_REVIEW)
    assert is_valid_transition(ScenarioState.IN_REVIEW, ScenarioState.APPROVED)
    assert is_valid_transition(ScenarioState.APPROVED, ScenarioState.PUBLISHED)


def test_invalid_transition_from_published() -> None:
    assert not is_valid_transition(ScenarioState.PUBLISHED, ScenarioState.DRAFT)


def test_owner_or_editor_can_edit_only_draft() -> None:
    assert can_edit_draft(
        collaborator_role=CollaboratorRole.OWNER,
        state=ScenarioState.DRAFT,
    )
    assert can_edit_draft(collaborator_role=CollaboratorRole.EDITOR, state=ScenarioState.DRAFT)
    assert not can_edit_draft(collaborator_role=None, state=ScenarioState.DRAFT)
    assert not can_edit_draft(
        collaborator_role=CollaboratorRole.OWNER,
        state=ScenarioState.IN_REVIEW,
    )


def test_submit_approve_publish_permissions() -> None:
    assert can_submit_for_review(
        actor_role=UserRole.AUTHOR,
        collaborator_role=CollaboratorRole.OWNER,
        state=ScenarioState.DRAFT,
    )
    assert not can_submit_for_review(
        actor_role=UserRole.AUTHOR,
        collaborator_role=CollaboratorRole.EDITOR,
        state=ScenarioState.DRAFT,
    )
    assert can_approve(actor_role=UserRole.REVIEWER, state=ScenarioState.IN_REVIEW)
    assert can_publish(actor_role=UserRole.REVIEWER, state=ScenarioState.APPROVED)
    assert not can_approve(actor_role=UserRole.AUTHOR, state=ScenarioState.IN_REVIEW)


def test_public_visibility() -> None:
    assert is_publicly_visible(ScenarioState.PUBLISHED)
    assert not is_publicly_visible(ScenarioState.DRAFT)


def test_collaboration_management_and_read_access() -> None:
    assert can_manage_collaborators(collaborator_role=CollaboratorRole.OWNER)
    assert not can_manage_collaborators(collaborator_role=CollaboratorRole.EDITOR)
    assert has_scenario_read_access(actor_role=UserRole.REVIEWER, collaborator_role=None)


def test_public_comment_view_and_write() -> None:
    pub = _scenario(state=ScenarioState.PUBLISHED)
    assert can_view_comments(scenario=pub, actor_role=None, collaborator_role=None)
    assert can_add_comment(scenario=pub, actor_role=UserRole.AUTHOR, collaborator_role=None)
    assert can_add_comment(scenario=pub, actor_role=UserRole.REVIEWER, collaborator_role=None)

    draft = _scenario(state=ScenarioState.DRAFT)
    assert not can_view_comments(scenario=draft, actor_role=None, collaborator_role=None)
    assert can_view_comments(scenario=draft, actor_role=UserRole.REVIEWER, collaborator_role=None)
    assert can_add_comment(
        scenario=draft,
        actor_role=UserRole.AUTHOR,
        collaborator_role=CollaboratorRole.OWNER,
    )
    assert not can_add_comment(
        scenario=draft,
        actor_role=UserRole.AUTHOR,
        collaborator_role=get_collaborator_role(scenario=draft, actor_user_id="stranger"),
    )
