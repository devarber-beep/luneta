"""Suggestion access rules and description paragraph helpers."""
from __future__ import annotations

from datetime import UTC, datetime

from app.core.description_paragraphs import replace_paragraph, split_paragraphs
from app.core.suggestion_access import (
    can_create_suggestion,
    can_list_suggestions,
    can_resolve_suggestion,
    can_see_suggestion_author_identity,
)
from app.domain.enums import CollaboratorRole, ScenarioState, UserAccountStatus, UserRole
from app.models.scenario import ScenarioCollaboratorModel, ScenarioModel
from app.models.user import UserModel


def _user(*, user_id: str, role: UserRole) -> UserModel:
    now = datetime.now(UTC)
    fn = user_id[:8]
    display = f"{fn} User"
    return UserModel(
        id=user_id,
        email_normalized=f"{user_id}@test.dev",
        role=role,
        account_status=UserAccountStatus.ACTIVE,
        email_verified_at=now,
        first_name=fn,
        last_name="User",
        display_name=display,
        display_name_normalized=display.lower(),
        password_hash="x",
        password_updated_at=now,
        created_at=now,
        updated_at=now,
    )


def _scenario(*, state: ScenarioState, author_id: str = "owner1") -> ScenarioModel:
    now = datetime.now(UTC)
    return ScenarioModel(
        id="s1",
        slug="test",
        title="T",
        description="First paragraph.\n\nSecond paragraph.",
        author_user_id=author_id,
        collaborators=[
            ScenarioCollaboratorModel(
                user_id=author_id,
                role=CollaboratorRole.OWNER,
                added_at=now,
                added_by=author_id,
            )
        ],
        state=state,
        last_state_changed_at=now,
        created_at=now,
        updated_at=now,
    )


def test_split_and_replace_paragraphs() -> None:
    text = "Alpha.\n\nBeta."
    parts = split_paragraphs(text)
    assert len(parts) == 2
    updated = replace_paragraph(description=text, paragraph_index=1, new_text="Gamma.")
    assert "Gamma." in updated
    assert "Alpha." in updated


def test_single_block_description_is_one_paragraph() -> None:
    assert split_paragraphs("Only one block without blank lines.") == [
        "Only one block without blank lines."
    ]


def test_investigator_can_suggest_on_published_not_own() -> None:
    scenario = _scenario(state=ScenarioState.PUBLISHED, author_id="owner1")
    user = _user(user_id="inv1", role=UserRole.INVESTIGATOR)
    assert can_create_suggestion(user=user, scenario=scenario, portfolio_investigator_ids=frozenset())
    assert not can_create_suggestion(
        user=_user(user_id="owner1", role=UserRole.INVESTIGATOR),
        scenario=scenario,
        portfolio_investigator_ids=frozenset(),
    )


def test_reviewer_can_suggest_during_in_review_even_in_portfolio() -> None:
    scenario = _scenario(state=ScenarioState.IN_REVIEW, author_id="inv-author")
    reviewer = _user(user_id="rev1", role=UserRole.REVIEWER)
    assert can_create_suggestion(
        user=reviewer,
        scenario=scenario,
        portfolio_investigator_ids=frozenset({"inv-author"}),
    )


def test_admin_can_suggest_on_others_in_review() -> None:
    scenario = _scenario(state=ScenarioState.IN_REVIEW, author_id="inv-author")
    admin = _user(user_id="adm1", role=UserRole.ADMIN)
    assert can_create_suggestion(user=admin, scenario=scenario, portfolio_investigator_ids=frozenset())


def test_owner_admin_and_suggester_list_suggestions() -> None:
    scenario = _scenario(state=ScenarioState.IN_REVIEW, author_id="owner1")
    assert can_list_suggestions(user=_user(user_id="owner1", role=UserRole.INVESTIGATOR), scenario=scenario)
    assert can_list_suggestions(user=_user(user_id="adm1", role=UserRole.ADMIN), scenario=scenario)
    assert can_list_suggestions(
        user=_user(user_id="inv2", role=UserRole.INVESTIGATOR),
        scenario=scenario,
        has_authored_suggestion=True,
    )
    assert can_list_suggestions(
        user=_user(user_id="rev1", role=UserRole.REVIEWER),
        scenario=scenario,
        portfolio_investigator_ids=frozenset({"owner1"}),
    )
    assert not can_list_suggestions(
        user=_user(user_id="rev1", role=UserRole.REVIEWER),
        scenario=scenario,
        portfolio_investigator_ids=frozenset(),
    )
    assert not can_list_suggestions(user=_user(user_id="inv2", role=UserRole.INVESTIGATOR), scenario=scenario)


def test_collaborator_can_list_suggestions() -> None:
    now = datetime.now(UTC)
    scenario = ScenarioModel(
        id="s1",
        slug="test",
        title="T",
        description="Body.",
        author_user_id="owner1",
        collaborators=[
            ScenarioCollaboratorModel(
                user_id="owner1",
                role=CollaboratorRole.OWNER,
                added_at=now,
                added_by="owner1",
            ),
            ScenarioCollaboratorModel(
                user_id="collab1",
                role=CollaboratorRole.COLLABORATOR,
                added_at=now,
                added_by="owner1",
            ),
        ],
        state=ScenarioState.PUBLISHED,
        last_state_changed_at=now,
        created_at=now,
        updated_at=now,
    )
    assert can_list_suggestions(
        user=_user(user_id="collab1", role=UserRole.INVESTIGATOR),
        scenario=scenario,
    )


def test_reviewer_cannot_suggest_on_published_they_already_reviewed() -> None:
    scenario = _scenario(state=ScenarioState.PUBLISHED, author_id="inv-author")
    reviewer = _user(user_id="rev1", role=UserRole.REVIEWER)
    assert not can_create_suggestion(
        user=reviewer,
        scenario=scenario,
        portfolio_investigator_ids=frozenset(),
        reviewer_has_reviewed_scenario=True,
    )


def test_reviewer_can_suggest_on_published_they_did_not_review() -> None:
    scenario = _scenario(state=ScenarioState.PUBLISHED, author_id="inv-author")
    reviewer = _user(user_id="rev2", role=UserRole.REVIEWER)
    assert can_create_suggestion(
        user=reviewer,
        scenario=scenario,
        portfolio_investigator_ids=frozenset({"inv-author"}),
        reviewer_has_reviewed_scenario=False,
    )


def test_only_owner_resolves() -> None:
    scenario = _scenario(state=ScenarioState.IN_REVIEW)
    assert can_resolve_suggestion(user=_user(user_id="owner1", role=UserRole.INVESTIGATOR), scenario=scenario)
    assert not can_resolve_suggestion(user=_user(user_id="inv2", role=UserRole.INVESTIGATOR), scenario=scenario)


def test_suggestion_author_identity_admin_only() -> None:
    assert can_see_suggestion_author_identity(user=_user(user_id="a1", role=UserRole.ADMIN))
    assert not can_see_suggestion_author_identity(user=_user(user_id="o1", role=UserRole.INVESTIGATOR))
    assert not can_see_suggestion_author_identity(user=_user(user_id="r1", role=UserRole.REVIEWER))
