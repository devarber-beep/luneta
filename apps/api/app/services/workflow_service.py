"""Workflow service for reviewer queue, approve and publish."""
from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException, status

from app.core.permissions import is_valid_transition
from app.core.scenario_access import can_approve_scenario, can_publish_scenario, can_reject_scenario
from app.domain.enums import ReviewEventType, ScenarioState, UserRole
from app.models.user import UserModel
from app.repositories.review_events import ReviewEventsRepository
from app.repositories.scenarios import ScenariosRepository
from app.repositories.users import UsersRepository
from app.schemas.workflow import ReviewQueueItem
from app.services.mailer_service import MailerService, NoopMailer


class WorkflowService:
    def __init__(
        self,
        *,
        scenarios_repo: ScenariosRepository,
        review_events_repo: ReviewEventsRepository,
        users_repo: UsersRepository,
        mailer: MailerService | NoopMailer | None = None,
    ) -> None:
        self._scenarios_repo = scenarios_repo
        self._review_events_repo = review_events_repo
        self._users_repo = users_repo
        self._mailer = mailer if mailer is not None else MailerService()

    async def review_queue(self, *, current_user: UserModel) -> list[ReviewQueueItem]:
        scenarios = await self._scenarios_repo.list_by_state(state=ScenarioState.IN_REVIEW)
        items: list[ReviewQueueItem] = []
        for scenario in scenarios:
            live_slug = scenario.public_slug if scenario.public_slug is not None else None
            live_title = scenario.public_title if scenario.public_title is not None else None
            live_body = scenario.public_body_markdown if scenario.public_body_markdown is not None else None
            items.append(
                ReviewQueueItem(
                    scenario_id=scenario.id or "",
                    slug=scenario.slug,
                    title=scenario.title,
                    author_user_id=scenario.author_user_id,
                    state=scenario.state,
                    has_prior_approval=scenario.first_approved_at is not None,
                    submitted_at=scenario.submitted_for_review_at or scenario.last_state_changed_at,
                    live_public_slug=live_slug,
                    live_public_title=live_title,
                    live_public_body_markdown=live_body,
                )
            )
        return items

    async def approve(self, *, scenario_id: str, current_user: UserModel):
        scenario = await self._scenarios_repo.get_by_id(scenario_id)
        if scenario is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")
        if not can_approve_scenario(user=current_user, scenario=scenario):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot approve this scenario")
        if not is_valid_transition(scenario.state, ScenarioState.APPROVED):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Invalid state transition")
        updated = await self._scenarios_repo.set_state(
            scenario_id=scenario_id,
            state=ScenarioState.APPROVED,
            actor_user_id=current_user.id or "",
        )
        if updated is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")
        await self._review_events_repo.create(
            scenario_id=updated.id or "",
            event_type=ReviewEventType.APPROVED,
            actor_user_id=current_user.id or "",
            actor_role=UserRole(current_user.role),
            from_state=scenario.state,
            to_state=updated.state,
        )
        return updated, datetime.now(UTC)

    async def reject(self, *, scenario_id: str, current_user: UserModel):
        scenario = await self._scenarios_repo.get_by_id(scenario_id)
        if scenario is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")
        if not can_reject_scenario(user=current_user, scenario=scenario):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot reject this scenario")
        if not is_valid_transition(scenario.state, ScenarioState.DRAFT):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Invalid state transition")
        updated = await self._scenarios_repo.reject_to_draft(scenario_id=scenario_id)
        if updated is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")
        await self._review_events_repo.create(
            scenario_id=updated.id or "",
            event_type=ReviewEventType.REJECTED,
            actor_user_id=current_user.id or "",
            actor_role=UserRole(current_user.role),
            from_state=scenario.state,
            to_state=updated.state,
        )
        return updated, datetime.now(UTC)

    async def publish(self, *, scenario_id: str, current_user: UserModel):
        scenario = await self._scenarios_repo.get_by_id(scenario_id)
        if scenario is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")
        if not can_publish_scenario(user=current_user, scenario=scenario):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot publish this scenario")
        if not is_valid_transition(scenario.state, ScenarioState.PUBLISHED):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Invalid state transition")
        updated = await self._scenarios_repo.set_state(
            scenario_id=scenario_id,
            state=ScenarioState.PUBLISHED,
            actor_user_id=current_user.id or "",
        )
        if updated is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")
        await self._review_events_repo.create(
            scenario_id=updated.id or "",
            event_type=ReviewEventType.PUBLISHED,
            actor_user_id=current_user.id or "",
            actor_role=UserRole(current_user.role),
            from_state=scenario.state,
            to_state=updated.state,
        )
        author = await self._users_repo.get_by_id(updated.author_user_id)
        slug = updated.public_slug or updated.slug
        title = updated.public_title or updated.title
        if author is not None and author.is_email_verified and slug:
            await self._mailer.send_scenario_live_to_author(
                to_email=author.email,
                scenario_title=title,
                public_slug=slug,
            )
        return updated, datetime.now(UTC)
