"""Authorization policy, contextual rules, and ownership constraints (Milestone 3)."""
from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.core.permissions import is_valid_transition
from app.core.rbac_policy import permissions_for_user, user_has_permission
from app.core.scenario_access import (
    can_publish_scenario,
    can_read_scenario,
    can_reject_scenario,
    can_submit_review,
)
from app.domain.authz_permissions import Permission
from app.domain.enums import ScenarioState, UserRole
from app.models.scenario import ScenarioModel
from app.models.user import UserModel


def _user(*, user_id: str, role: UserRole) -> UserModel:
    now = datetime.now(UTC)
    return UserModel(
        _id=user_id,
        email=f"{user_id}@test.dev",
        email_normalized=f"{user_id}@test.dev",
        password_hash="x",
        password_updated_at=now,
        role=role,
        is_email_verified=True,
        email_verified_at=now,
        nickname=user_id[:8],
        nickname_normalized=user_id[:8],
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
        body_markdown="b",
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


def test_rbac_reviewer_has_queue_and_workflow_permissions() -> None:
    u = _user(user_id="r1", role=UserRole.COORDINATOR)
    assert user_has_permission(user=u, permission=Permission.SCENARIO_READ_REVIEW_QUEUE)
    assert user_has_permission(user=u, permission=Permission.SCENARIO_PUBLISH)


def test_coordinator_cannot_publish_own_submission() -> None:
    coord = _user(user_id="same", role=UserRole.COORDINATOR)
    sc = _scenario(author_id="same", state=ScenarioState.IN_REVIEW)
    assert not can_publish_scenario(user=coord, scenario=sc)


def test_coordinator_can_publish_others_in_review() -> None:
    coord = _user(user_id="r1", role=UserRole.COORDINATOR)
    sc = _scenario(author_id="a1", state=ScenarioState.IN_REVIEW)
    assert can_publish_scenario(user=coord, scenario=sc)


def test_coordinator_cannot_reject_own_submission() -> None:
    coord = _user(user_id="same", role=UserRole.COORDINATOR)
    sc = _scenario(author_id="same", state=ScenarioState.IN_REVIEW)
    assert not can_reject_scenario(user=coord, scenario=sc)


def test_author_cannot_read_others_draft() -> None:
    author = _user(user_id="u1", role=UserRole.INVESTIGATOR)
    other_draft = _scenario(author_id="other", state=ScenarioState.DRAFT)
    assert not can_read_scenario(user=author, scenario=other_draft)


def test_author_can_read_published_by_others() -> None:
    author = _user(user_id="u1", role=UserRole.INVESTIGATOR)
    pub = _scenario(author_id="other", state=ScenarioState.PUBLISHED)
    assert can_read_scenario(user=author, scenario=pub)


def test_coordinator_cannot_read_others_draft_outside_queue_states() -> None:
    coord = _user(user_id="r1", role=UserRole.COORDINATOR)
    draft = _scenario(author_id="a1", state=ScenarioState.DRAFT)
    assert not can_read_scenario(user=coord, scenario=draft)


def test_coordinator_can_read_others_in_review() -> None:
    coord = _user(user_id="r1", role=UserRole.COORDINATOR)
    sc = _scenario(author_id="a1", state=ScenarioState.IN_REVIEW)
    assert can_read_scenario(user=coord, scenario=sc)


def test_reviewer_can_submit_own_draft_as_owner() -> None:
    """Coordinators can create drafts; submit still requires scenario owner collaborator."""
    rev = _user(user_id="owner", role=UserRole.COORDINATOR)
    sc = _scenario(author_id="owner", state=ScenarioState.DRAFT)
    assert can_submit_review(user=rev, scenario=sc)


def test_in_review_to_draft_is_valid_reject_transition() -> None:
    assert is_valid_transition(ScenarioState.IN_REVIEW, ScenarioState.DRAFT)


@pytest.mark.asyncio
async def test_http_reviewer_cannot_publish_own_scenario(api_client) -> None:
    """Regression: self-publish from review must be rejected at the service/policy layer."""
    from unittest.mock import patch

    with patch("app.services.email_verification_service.secrets.token_urlsafe", return_value="rev-self-token"):
        signup = await api_client.post(
            "/auth/signup",
            json={
                "email": "selfrev@luneta.dev",
                "password": "Password123!",
                "role": "coordinator",
                "nickname": "selfrev",
            },
        )
        assert signup.status_code == 200
        await api_client.post("/auth/verify-email", json={"token": "rev-self-token"})
    login = await api_client.post(
        "/auth/login",
        json={"email": "selfrev@luneta.dev", "password": "Password123!"},
    )
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    create = await api_client.post(
        "/scenarios",
        json={"title": "Own", "body_markdown": "x"},
        headers=headers,
    )
    assert create.status_code == 200
    sid = create.json()["id"]
    sub = await api_client.post(f"/scenarios/{sid}/submit-review", headers=headers)
    assert sub.status_code == 200
    pub = await api_client.post(f"/workflow/scenarios/{sid}/publish", headers=headers)
    assert pub.status_code == 403
