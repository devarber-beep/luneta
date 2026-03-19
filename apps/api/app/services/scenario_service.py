"""Scenario service for draft/edit/submit flow."""
from __future__ import annotations

from fastapi import HTTPException, status

from app.core.permissions import can_edit_draft, can_submit_for_review, is_valid_transition
from app.domain.enums import ReviewEventType, ScenarioState, UserRole
from app.models.scenario import ScenarioModel
from app.models.user import UserModel
from app.repositories.review_events import ReviewEventsRepository
from app.repositories.scenario_revisions import ScenarioRevisionsRepository
from app.repositories.scenarios import ScenariosRepository


class ScenarioService:
    def __init__(
        self,
        *,
        scenarios_repo: ScenariosRepository,
        revisions_repo: ScenarioRevisionsRepository,
        review_events_repo: ReviewEventsRepository,
    ) -> None:
        self._scenarios_repo = scenarios_repo
        self._revisions_repo = revisions_repo
        self._review_events_repo = review_events_repo

    async def create_draft(
        self,
        *,
        current_user: UserModel,
        slug: str,
        title: str,
        body_markdown: str,
    ) -> ScenarioModel:
        if current_user.role != UserRole.AUTHOR:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only authors can create drafts")

        await self._scenarios_repo.ensure_indexes()
        await self._revisions_repo.ensure_indexes()
        await self._review_events_repo.ensure_indexes()

        scenario = await self._scenarios_repo.create(
            slug=slug,
            title=title,
            body_markdown=body_markdown,
            author_user_id=current_user.id or "",
        )
        await self._revisions_repo.create_snapshot(
            scenario_id=scenario.id or "",
            revision_number=scenario.current_revision_number,
            title=scenario.title,
            body_markdown=scenario.body_markdown,
            state_snapshot=scenario.state,
            created_by_user_id=current_user.id or "",
        )
        await self._review_events_repo.create(
            scenario_id=scenario.id or "",
            event_type=ReviewEventType.DRAFT_SAVED,
            actor_user_id=current_user.id or "",
        )
        return scenario

    async def get_for_author_or_reviewer(self, *, scenario_id: str, current_user: UserModel) -> ScenarioModel:
        scenario = await self._scenarios_repo.get_by_id(scenario_id)
        if scenario is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")

        # Reviewer can see all scenarios; author only own.
        if current_user.role != UserRole.REVIEWER and scenario.author_user_id != (current_user.id or ""):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        return scenario

    async def patch_draft(
        self,
        *,
        scenario_id: str,
        current_user: UserModel,
        title: str | None,
        body_markdown: str | None,
    ) -> ScenarioModel:
        scenario = await self._scenarios_repo.get_by_id(scenario_id)
        if scenario is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")

        actor_user_id = current_user.id or ""
        if not can_edit_draft(
            actor_user_id=actor_user_id,
            author_user_id=scenario.author_user_id,
            state=scenario.state,
        ):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only author can edit draft")

        updated = await self._scenarios_repo.update_draft_content(
            scenario_id=scenario_id,
            title=title,
            body_markdown=body_markdown,
        )
        if updated is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")

        bumped = await self._scenarios_repo.bump_revision_number(scenario_id=scenario_id)
        if bumped is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")

        await self._revisions_repo.create_snapshot(
            scenario_id=bumped.id or "",
            revision_number=bumped.current_revision_number,
            title=bumped.title,
            body_markdown=bumped.body_markdown,
            state_snapshot=bumped.state,
            created_by_user_id=actor_user_id,
        )
        await self._review_events_repo.create(
            scenario_id=bumped.id or "",
            event_type=ReviewEventType.DRAFT_SAVED,
            actor_user_id=actor_user_id,
        )
        return bumped

    async def submit_review(self, *, scenario_id: str, current_user: UserModel) -> ScenarioModel:
        scenario = await self._scenarios_repo.get_by_id(scenario_id)
        if scenario is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")

        actor_user_id = current_user.id or ""
        actor_role = UserRole(current_user.role)
        if not can_submit_for_review(
            actor_role=actor_role,
            actor_user_id=actor_user_id,
            author_user_id=scenario.author_user_id,
            state=scenario.state,
        ):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot submit this scenario")

        if not is_valid_transition(scenario.state, ScenarioState.IN_REVIEW):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Invalid state transition")

        updated = await self._scenarios_repo.set_state(
            scenario_id=scenario_id,
            state=ScenarioState.IN_REVIEW,
        )
        if updated is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")

        await self._review_events_repo.create(
            scenario_id=updated.id or "",
            event_type=ReviewEventType.SUBMITTED,
            actor_user_id=actor_user_id,
            from_state=scenario.state,
            to_state=updated.state,
        )
        return updated
