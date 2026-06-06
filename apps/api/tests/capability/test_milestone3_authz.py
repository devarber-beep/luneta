"""Authorization policy, contextual rules, and ownership constraints (capability tests)."""
from __future__ import annotations

from datetime import UTC, datetime

from app.core.permissions import is_valid_transition
from app.core.rbac_policy import permissions_for_user, user_has_permission
from app.core.scenario_access import (
    can_publish_scenario,
    can_read_scenario,
    can_request_changes_scenario,
    can_submit_review,
)
from app.domain.authz_permissions import Permission
from app.domain.enums import ScenarioState, UserRole
from app.models.scenario import ScenarioModel
from app.models.user import UserModel


def _user(*, user_id: str, role: UserRole) -> UserModel:
    now = datetime.now(UTC)
    fn = user_id[:8]
    display = f"{fn} User"
    return UserModel(
        _id=user_id,
        email_normalized=f"{user_id}@test.dev",
        password_hash="x",
        password_updated_at=now,
        role=role,
        email_verified_at=now,
        first_name=fn,
        last_name="User",
        display_name=display,
        display_name_normalized=display.lower(),
        created_at=now,
        updated_at=now,
    )


def _scenario(
    *,
    author_id: str = "a1",
    state: ScenarioState = ScenarioState.DRAFT,
    collaborators: list | None = None,
) -> ScenarioModel:
    now = datetime.now(UTC)
    cols = collaborators if collaborators is not None else []
    return ScenarioModel(
        _id="sc1",
        slug="slug",
        title="t",
        description="d",
        author_user_id=author_id,
        collaborators=cols,
        state=state,
        current_revision_number=1,
        last_state_changed_at=now,
        created_at=now,
        updated_at=now,
    )


def test_rbac_author_cannot_publish() -> None:
    u = _user(user_id="u1", role=UserRole.INVESTIGATOR)
    perms = permissions_for_user(user=u)
    assert Permission.SCENARIO_PUBLISH not in perms
    assert Permission.SCENARIO_READ_REVIEW_QUEUE not in perms
    assert Permission.SCENARIO_CREATE_DRAFT in perms


def test_rbac_registered_user_permissions() -> None:
    u = _user(user_id="reg1", role=UserRole.REGISTERED)
    perms = permissions_for_user(user=u)
    assert Permission.SCENARIO_READ_PUBLIC in perms
    assert Permission.SCENARIO_EVALUATE_PUBLISHED in perms
    assert Permission.SCENARIO_CREATE_DRAFT not in perms


def test_rbac_reviewer_has_queue_and_workflow_permissions() -> None:
    u = _user(user_id="r1", role=UserRole.REVIEWER)
    assert user_has_permission(user=u, permission=Permission.SCENARIO_READ_REVIEW_QUEUE)
    assert user_has_permission(user=u, permission=Permission.SCENARIO_PUBLISH)


def test_rbac_admin_has_reviewer_permissions_plus_user_admin_actions() -> None:
    admin_perms = permissions_for_user(user=_user(user_id="a1", role=UserRole.ADMIN))
    reviewer_perms = permissions_for_user(user=_user(user_id="r1", role=UserRole.REVIEWER))
    assert reviewer_perms <= admin_perms
    assert Permission.USER_ADMIN_CREATE_INVESTIGATOR in admin_perms
    assert Permission.USER_ADMIN_SET_USER_ROLE in admin_perms
    assert Permission.USER_ADMIN_SET_ACCOUNT_STATUS in admin_perms
    assert Permission.USER_ADMIN_READ_ANY_PROFILE in admin_perms
    assert Permission.USER_ADMIN_MANAGE_REVIEWER_ASSIGNMENTS in admin_perms
    assert Permission.USER_ADMIN_CREATE_INVESTIGATOR not in reviewer_perms


def test_reviewer_cannot_publish_own_submission() -> None:
    rev = _user(user_id="same", role=UserRole.REVIEWER)
    sc = _scenario(author_id="same", state=ScenarioState.IN_REVIEW)
    assert not can_publish_scenario(user=rev, scenario=sc)


def test_reviewer_can_publish_others_in_review_when_in_portfolio() -> None:
    rev = _user(user_id="r1", role=UserRole.REVIEWER)
    sc = _scenario(author_id="a1", state=ScenarioState.IN_REVIEW)
    assert can_publish_scenario(
        user=rev, scenario=sc, portfolio_investigator_ids=frozenset({"a1"})
    )


def test_reviewer_cannot_publish_outside_portfolio() -> None:
    rev = _user(user_id="r1", role=UserRole.REVIEWER)
    sc = _scenario(author_id="a1", state=ScenarioState.IN_REVIEW)
    assert not can_publish_scenario(user=rev, scenario=sc, portfolio_investigator_ids=frozenset())


def test_admin_can_publish_own_submission() -> None:
    admin = _user(user_id="same", role=UserRole.ADMIN)
    sc = _scenario(author_id="same", state=ScenarioState.IN_REVIEW)
    assert can_publish_scenario(user=admin, scenario=sc)


def test_reviewer_cannot_request_changes_on_own_submission() -> None:
    rev = _user(user_id="same", role=UserRole.REVIEWER)
    sc = _scenario(author_id="same", state=ScenarioState.IN_REVIEW)
    assert not can_request_changes_scenario(user=rev, scenario=sc)


def test_admin_can_request_changes_on_own_submission() -> None:
    admin = _user(user_id="same", role=UserRole.ADMIN)
    sc = _scenario(author_id="same", state=ScenarioState.IN_REVIEW)
    assert can_request_changes_scenario(user=admin, scenario=sc)


def test_author_cannot_read_others_draft() -> None:
    author = _user(user_id="u1", role=UserRole.INVESTIGATOR)
    other_draft = _scenario(author_id="other", state=ScenarioState.DRAFT)
    assert not can_read_scenario(user=author, scenario=other_draft)


def test_author_can_read_published_by_others() -> None:
    author = _user(user_id="u1", role=UserRole.INVESTIGATOR)
    now = datetime.now(UTC)
    pub = _scenario(author_id="other", state=ScenarioState.PUBLISHED).model_copy(
        update={
            "published_at": now,
            "public_slug": "slug",
            "public_title": "t",
            "public_description": "d",
        }
    )
    assert can_read_scenario(user=author, scenario=pub)


def test_reviewer_cannot_read_others_draft_outside_queue_states() -> None:
    rev = _user(user_id="r1", role=UserRole.REVIEWER)
    draft = _scenario(author_id="a1", state=ScenarioState.DRAFT)
    assert not can_read_scenario(user=rev, scenario=draft)


def test_reviewer_can_read_others_in_review_when_in_portfolio() -> None:
    rev = _user(user_id="r1", role=UserRole.REVIEWER)
    sc = _scenario(author_id="a1", state=ScenarioState.IN_REVIEW)
    assert can_read_scenario(user=rev, scenario=sc, portfolio_investigator_ids=frozenset({"a1"}))


def test_reviewer_can_submit_own_draft_as_owner() -> None:
    """Reviewers inherit investigator capabilities; submit still requires owner collaborator."""
    rev = _user(user_id="owner", role=UserRole.REVIEWER)
    sc = _scenario(author_id="owner", state=ScenarioState.DRAFT)
    assert can_submit_review(user=rev, scenario=sc)


def test_in_review_to_changes_required_is_valid() -> None:
    assert is_valid_transition(ScenarioState.IN_REVIEW, ScenarioState.CHANGES_REQUIRED)
