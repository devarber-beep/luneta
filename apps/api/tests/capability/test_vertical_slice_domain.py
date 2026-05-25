"""Tests for domain workflow and permissions rules."""
from datetime import UTC, datetime

from app.core.permissions import (
    can_edit_draft,
    can_edit_published_content,
    can_manage_collaborators,
    can_start_applying_changes,
    can_submit_for_review,
    has_republication_pending,
    is_publicly_visible,
    is_valid_transition,
)
from app.core.scenario_access import can_publish_scenario, can_read_scenario, can_request_changes_scenario
from app.domain.enums import CollaboratorRole, ScenarioState, UserAccountStatus, UserRole
from app.models.scenario import ScenarioModel
from app.models.user import UserModel


def _scenario(*, state: ScenarioState) -> ScenarioModel:
    now = datetime.now(UTC)
    published_at = now if state == ScenarioState.PUBLISHED else None
    public_slug = public_title = public_description = None
    if state == ScenarioState.PUBLISHED:
        public_slug = "s"
        public_title = "t"
        public_description = "d"
    return ScenarioModel(
        _id="1",
        slug="s",
        title="t",
        description="d",
        author_user_id="u1",
        collaborators=[],
        state=state,
        current_revision_number=1,
        published_at=published_at,
        first_published_at=published_at,
        public_slug=public_slug,
        public_title=public_title,
        public_description=public_description,
        first_approved_at=published_at,
        last_state_changed_at=now,
        created_at=now,
        updated_at=now,
    )


def test_valid_transitions() -> None:
    assert is_valid_transition(ScenarioState.DRAFT, ScenarioState.QUEUED)
    assert is_valid_transition(ScenarioState.QUEUED, ScenarioState.IN_REVIEW)
    assert is_valid_transition(ScenarioState.IN_REVIEW, ScenarioState.PUBLISHED)
    assert is_valid_transition(ScenarioState.IN_REVIEW, ScenarioState.CHANGES_REQUIRED)
    assert is_valid_transition(ScenarioState.CHANGES_REQUIRED, ScenarioState.APPLYING_CHANGES)
    assert is_valid_transition(ScenarioState.APPLYING_CHANGES, ScenarioState.QUEUED)
    assert is_valid_transition(ScenarioState.PUBLISHED, ScenarioState.QUEUED)


def test_invalid_transition_from_published_to_draft() -> None:
    assert not is_valid_transition(ScenarioState.PUBLISHED, ScenarioState.DRAFT)


def test_owner_or_collaborator_can_edit_only_draft_or_applying() -> None:
    assert can_edit_draft(
        collaborator_role=CollaboratorRole.OWNER,
        state=ScenarioState.DRAFT,
    )
    assert can_edit_draft(
        collaborator_role=CollaboratorRole.OWNER,
        state=ScenarioState.APPLYING_CHANGES,
    )
    assert not can_edit_draft(collaborator_role=CollaboratorRole.COLLABORATOR, state=ScenarioState.DRAFT)
    assert not can_edit_draft(collaborator_role=None, state=ScenarioState.DRAFT)
    assert not can_edit_draft(
        collaborator_role=CollaboratorRole.OWNER,
        state=ScenarioState.QUEUED,
    )


def test_only_owner_can_edit_published_content() -> None:
    assert can_edit_published_content(collaborator_role=CollaboratorRole.OWNER)
    assert not can_edit_published_content(collaborator_role=CollaboratorRole.COLLABORATOR)
    assert not can_edit_published_content(collaborator_role=None)


def test_submit_approve_publish_permissions() -> None:
    draft = _scenario(state=ScenarioState.DRAFT)
    assert can_submit_for_review(
        collaborator_role=CollaboratorRole.OWNER,
        state=ScenarioState.DRAFT,
        scenario=draft,
    )
    assert not can_submit_for_review(
        collaborator_role=CollaboratorRole.COLLABORATOR,
        state=ScenarioState.DRAFT,
        scenario=draft,
    )
    now = datetime.now(UTC)
    published_aligned = ScenarioModel(
        _id="1",
        slug="s",
        title="t",
        description="d",
        author_user_id="u1",
        collaborators=[],
        state=ScenarioState.PUBLISHED,
        current_revision_number=1,
        published_at=now,
        first_published_at=now,
        public_slug="s",
        public_title="t",
        public_description="d",
        first_approved_at=now,
        last_state_changed_at=now,
        created_at=now,
        updated_at=now,
    )
    assert not can_submit_for_review(
        collaborator_role=CollaboratorRole.OWNER,
        state=ScenarioState.PUBLISHED,
        scenario=published_aligned,
    )
    published_pending = published_aligned.model_copy(
        update={"title": "t2", "slug": "s2"},
    )
    assert has_republication_pending(scenario=published_pending)
    assert can_submit_for_review(
        collaborator_role=CollaboratorRole.OWNER,
        state=ScenarioState.PUBLISHED,
        scenario=published_pending,
    )
    assert can_start_applying_changes(
        collaborator_role=CollaboratorRole.OWNER,
        state=ScenarioState.CHANGES_REQUIRED,
    )


def test_reviewer_cannot_publish_own_submission() -> None:
    now = datetime.now(UTC)
    reviewer = UserModel(
        _id="rev",
        email_normalized="r@example.com",
        password_hash="x",
        password_updated_at=now,
        nickname="reviewer",
        nickname_normalized="reviewer",
        role=UserRole.REVIEWER,
        account_status=UserAccountStatus.ACTIVE,
        email_verified_at=now,
        created_at=now,
        updated_at=now,
    )
    in_review_own = _scenario(state=ScenarioState.IN_REVIEW).model_copy(update={"author_user_id": "rev"})
    assert not can_publish_scenario(user=reviewer, scenario=in_review_own)


def test_public_visibility() -> None:
    published = _scenario(state=ScenarioState.PUBLISHED)
    assert is_publicly_visible(scenario=published)
    draft = _scenario(state=ScenarioState.DRAFT)
    assert not is_publicly_visible(scenario=draft)
    not_suitable = _scenario(state=ScenarioState.NOT_SUITABLE)
    not_suitable = not_suitable.model_copy(update={"published_at": datetime.now(UTC), "public_slug": "s"})
    assert not is_publicly_visible(scenario=not_suitable)


def test_reviewer_read_in_portfolio_states() -> None:
    now = datetime.now(UTC)
    reviewer = UserModel(
        _id="rev",
        email_normalized="r@example.com",
        password_hash="x",
        password_updated_at=now,
        nickname="reviewer",
        nickname_normalized="reviewer",
        role=UserRole.REVIEWER,
        account_status=UserAccountStatus.ACTIVE,
        email_verified_at=now,
        created_at=now,
        updated_at=now,
    )
    queued_other = _scenario(state=ScenarioState.QUEUED).model_copy(update={"author_user_id": "other"})
    assert can_read_scenario(
        user=reviewer,
        scenario=queued_other,
        portfolio_investigator_ids=frozenset({"other"}),
    )
    assert can_request_changes_scenario(
        user=reviewer,
        scenario=_scenario(state=ScenarioState.IN_REVIEW).model_copy(update={"author_user_id": "other"}),
        portfolio_investigator_ids=frozenset({"other"}),
    )


def test_manage_collaborators_owner_only() -> None:
    assert can_manage_collaborators(collaborator_role=CollaboratorRole.OWNER)
    assert not can_manage_collaborators(collaborator_role=CollaboratorRole.COLLABORATOR)
