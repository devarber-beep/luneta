"""Tests for domain workflow and permissions rules."""
from datetime import UTC, datetime

from app.core.permissions import (
    can_approve,
    can_edit_draft,
    can_edit_published_content,
    can_manage_collaborators,
    can_publish,
    can_submit_for_review,
    has_republication_pending,
    has_scenario_read_access,
    is_publicly_visible,
    is_valid_transition,
)
from app.domain.enums import CollaboratorRole, ScenarioState, UserRole
from app.models.scenario import ScenarioModel


def _scenario(*, state: ScenarioState) -> ScenarioModel:
    now = datetime.now(UTC)
    published_at = now if state == ScenarioState.PUBLISHED else None
    public_slug = public_title = public_body = None
    if state == ScenarioState.PUBLISHED:
        public_slug = "s"
        public_title = "t"
        public_body = "b"
    return ScenarioModel(
        _id="1",
        slug="s",
        title="t",
        body_markdown="b",
        author_user_id="u1",
        collaborators=[],
        state=state,
        current_revision_number=1,
        published_at=published_at,
        first_published_at=published_at,
        public_slug=public_slug,
        public_title=public_title,
        public_body_markdown=public_body,
        first_approved_at=published_at,
        last_state_changed_at=now,
        created_at=now,
        updated_at=now,
    )


def test_valid_transitions() -> None:
    assert is_valid_transition(ScenarioState.DRAFT, ScenarioState.IN_REVIEW)
    assert is_valid_transition(ScenarioState.IN_REVIEW, ScenarioState.APPROVED)
    assert is_valid_transition(ScenarioState.APPROVED, ScenarioState.PUBLISHED)
    assert is_valid_transition(ScenarioState.PUBLISHED, ScenarioState.IN_REVIEW)


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


def test_only_owner_can_edit_published_content() -> None:
    assert can_edit_published_content(collaborator_role=CollaboratorRole.OWNER)
    assert not can_edit_published_content(collaborator_role=CollaboratorRole.EDITOR)
    assert not can_edit_published_content(collaborator_role=None)


def test_submit_approve_publish_permissions() -> None:
    draft = _scenario(state=ScenarioState.DRAFT)
    assert can_submit_for_review(
        actor_role=UserRole.AUTHOR,
        collaborator_role=CollaboratorRole.OWNER,
        state=ScenarioState.DRAFT,
        scenario=draft,
    )
    assert not can_submit_for_review(
        actor_role=UserRole.AUTHOR,
        collaborator_role=CollaboratorRole.EDITOR,
        state=ScenarioState.DRAFT,
        scenario=draft,
    )
    now = datetime.now(UTC)
    published_aligned = ScenarioModel(
        _id="1",
        slug="s",
        title="t",
        body_markdown="b",
        author_user_id="u1",
        collaborators=[],
        state=ScenarioState.PUBLISHED,
        current_revision_number=1,
        published_at=now,
        first_published_at=now,
        public_slug="s",
        public_title="t",
        public_body_markdown="b",
        first_approved_at=now,
        last_state_changed_at=now,
        created_at=now,
        updated_at=now,
    )
    assert not can_submit_for_review(
        actor_role=UserRole.AUTHOR,
        collaborator_role=CollaboratorRole.OWNER,
        state=ScenarioState.PUBLISHED,
        scenario=published_aligned,
    )
    published_pending = published_aligned.model_copy(
        update={"title": "t2", "slug": "s2"},
    )
    assert has_republication_pending(scenario=published_pending)
    assert can_submit_for_review(
        actor_role=UserRole.AUTHOR,
        collaborator_role=CollaboratorRole.OWNER,
        state=ScenarioState.PUBLISHED,
        scenario=published_pending,
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


