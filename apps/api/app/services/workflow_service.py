"""Workflow service for reviewer queue, approve and publish."""
from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException, status

from app.core.permissions import can_approve, can_publish, is_valid_transition
from app.domain.enums import ReviewEventType, ScenarioState, UserRole
from app.models.user import UserModel
from app.repositories.review_events import ReviewEventsRepository
from app.repositories.scenarios import ScenariosRepository
from app.schemas.workflow import ReviewQueueItem


class WorkflowService:
    def __init__(
        self,
        *,
        scenarios_repo: ScenariosRepository,
        review_events_repo: ReviewEventsRepository,
    ) -> None:
        self._scenarios_repo = scenarios_repo
        self._review_events_repo = review_events_repo

    async def review_queue(self, *, current_user: UserModel) -> list[ReviewQueueItem]:
        if current_user.role != UserRole.REVIEWER:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only reviewer can access queue")
        scenarios = await self._scenarios_repo.list_by_state(state=ScenarioState.IN_REVIEW)
        items: list[ReviewQueueItem] = []
        for scenario in scenarios:
            items.append(
                ReviewQueueItem(
                    scenario_id=scenario.id or "",
                    slug=scenario.slug,
                    title=scenario.title,
                    author_user_id=scenario.author_user_id,
                    state=scenario.state,
                    submitted_at=scenario.updated_at,
                )
            )
        return items

    async def approve(self, *, scenario_id: str, current_user: UserModel):
        scenario = await self._scenarios_repo.get_by_id(scenario_id)
        if scenario is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")
        actor_role = UserRole(current_user.role)
        if not can_approve(actor_role=actor_role, state=scenario.state):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot approve this scenario")
        if not is_valid_transition(scenario.state, ScenarioState.APPROVED):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Invalid state transition")
        updated = await self._scenarios_repo.set_state(scenario_id=scenario_id, state=ScenarioState.APPROVED)
        if updated is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")
        await self._review_events_repo.create(
            scenario_id=updated.id or "",
            event_type=ReviewEventType.APPROVED,
            actor_user_id=current_user.id or "",
            from_state=scenario.state,
            to_state=updated.state,
        )
        return updated, datetime.now(UTC)

    async def publish(self, *, scenario_id: str, current_user: UserModel):
        scenario = await self._scenarios_repo.get_by_id(scenario_id)
        if scenario is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")
        actor_role = UserRole(current_user.role)
        if not can_publish(actor_role=actor_role, state=scenario.state):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot publish this scenario")
        if not is_valid_transition(scenario.state, ScenarioState.PUBLISHED):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Invalid state transition")
        updated = await self._scenarios_repo.set_state(scenario_id=scenario_id, state=ScenarioState.PUBLISHED)
        if updated is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")
        await self._review_events_repo.create(
            scenario_id=updated.id or "",
            event_type=ReviewEventType.PUBLISHED,
            actor_user_id=current_user.id or "",
            from_state=scenario.state,
            to_state=updated.state,
        )
        return updated, datetime.now(UTC)
