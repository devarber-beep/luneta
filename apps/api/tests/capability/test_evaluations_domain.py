"""Domain rules for ethical evaluations."""
from datetime import UTC, datetime

from app.core.evaluation_access import (
    can_read_evaluation_comments,
    can_read_evaluation_detail,
    can_read_evaluation_summary,
    can_submit_evaluation,
)
from app.domain.enums import ScenarioState, UserRole
from app.models.scenario import ScenarioCollaboratorModel, ScenarioModel
from app.models.user import UserModel


def _scenario(*, author_id: str = "author-1", state: ScenarioState = ScenarioState.PUBLISHED) -> ScenarioModel:
    now = datetime.now(UTC)
    published = state == ScenarioState.PUBLISHED
    return ScenarioModel(
        _id="sc-1",
        author_user_id=author_id,
        title="Published",
        description="Body",
        slug="published-sc",
        state=state,
        collaborators=[
            ScenarioCollaboratorModel(
                user_id=author_id,
                role="owner",
                added_at=now,
                added_by=author_id,
            )
        ],
        published_at=now if published else None,
        public_slug="published-sc" if published else None,
        public_title="Published" if published else None,
        public_description="Body" if published else None,
        last_state_changed_at=now,
        created_at=now,
        updated_at=now,
    )


def _user(*, uid: str, role: UserRole) -> UserModel:
    now = datetime.now(UTC)
    return UserModel(
        _id=uid,
        email_normalized=f"{uid}@luneta.dev",
        password_hash="x",
        password_updated_at=now,
        role=role,
        email_verified_at=now,
        nickname=uid,
        nickname_normalized=uid,
        created_at=now,
        updated_at=now,
    )


def test_registered_can_evaluate_others_published() -> None:
    scenario = _scenario()
    user = _user(uid="reg-1", role=UserRole.REGISTERED)
    assert can_submit_evaluation(user=user, scenario=scenario)


def test_owner_cannot_evaluate_own_scenario() -> None:
    scenario = _scenario(author_id="author-1")
    user = _user(uid="author-1", role=UserRole.INVESTIGATOR)
    assert not can_submit_evaluation(user=user, scenario=scenario)


def test_owner_can_read_summary_and_comments_not_detail() -> None:
    scenario = _scenario(author_id="author-1")
    owner = _user(uid="author-1", role=UserRole.INVESTIGATOR)
    assert not can_submit_evaluation(user=owner, scenario=scenario)
    assert can_read_evaluation_summary(user=owner, scenario=scenario)
    assert can_read_evaluation_comments(user=owner, scenario=scenario)
    assert not can_read_evaluation_detail(user=owner, scenario=scenario)


def test_admin_can_read_detail() -> None:
    scenario = _scenario()
    admin = _user(uid="admin-1", role=UserRole.ADMIN)
    assert can_read_evaluation_detail(user=admin, scenario=scenario)
    assert not can_read_evaluation_comments(user=admin, scenario=scenario)


def test_reviewer_can_read_summary_not_detail() -> None:
    scenario = _scenario(author_id="author-1")
    reviewer = _user(uid="rev-1", role=UserRole.REVIEWER)
    assert can_read_evaluation_summary(user=reviewer, scenario=scenario)
    assert not can_read_evaluation_detail(user=reviewer, scenario=scenario)


def test_registered_can_read_summary() -> None:
    scenario = _scenario()
    user = _user(uid="reg-1", role=UserRole.REGISTERED)
    assert can_read_evaluation_summary(user=user, scenario=scenario)
    assert not can_read_evaluation_detail(user=user, scenario=scenario)


def test_draft_not_evaluable() -> None:
    scenario = _scenario(state=ScenarioState.DRAFT)
    user = _user(uid="reg-1", role=UserRole.REGISTERED)
    assert not can_submit_evaluation(user=user, scenario=scenario)
