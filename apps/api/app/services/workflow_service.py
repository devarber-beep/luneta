"""Workflow service for reviewer queue, review actions, and publish."""
from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException, status

from app.core.permissions import is_valid_transition
from app.core.scenario_access import (
    can_mark_not_suitable_scenario,
    can_publish_scenario,
    can_reopen_not_suitable,
    can_request_changes_scenario,
    can_start_review_scenario,
)
from app.core.reviewer_portfolio import reviewer_has_investigator_in_portfolio
from app.domain.enums import AuditActionType, ReviewEventType, ScenarioState, UserRole
from app.models.user import UserModel
from app.repositories.review_events import ReviewEventsRepository
from app.repositories.reviewer_assignments import ReviewerAssignmentsRepository
from app.repositories.scenarios import ScenariosRepository
from app.repositories.suggestions import SuggestionsRepository
from app.repositories.users import UsersRepository
from app.schemas.workflow import ReviewQueueItem, ReviewedScenarioItem
from app.services.audit_helpers import record_scenario_audit
from app.services.audit_service import AuditService
from app.services.notification_service import NotificationService
from app.services.portfolio_loader import portfolio_investigator_ids_for_user


class WorkflowService:
    def __init__(
        self,
        *,
        scenarios_repo: ScenariosRepository,
        review_events_repo: ReviewEventsRepository,
        users_repo: UsersRepository,
        assignments_repo: ReviewerAssignmentsRepository,
        suggestions_repo: SuggestionsRepository | None = None,
        notification_service: NotificationService | None = None,
        audit_service: AuditService | None = None,
    ) -> None:
        self._scenarios_repo = scenarios_repo
        self._review_events_repo = review_events_repo
        self._users_repo = users_repo
        self._assignments_repo = assignments_repo
        self._suggestions_repo = suggestions_repo
        self._notifications = notification_service
        self._audit = audit_service

    async def review_queue(
        self,
        *,
        current_user: UserModel,
        q: str | None = None,
        category_ids: list[str] | None = None,
    ) -> list[ReviewQueueItem]:
        author_ids_from_name: list[str] | None = None
        trimmed_q = (q or "").strip()
        if trimmed_q:
            author_ids_from_name = await self._users_repo.list_ids_matching_display_name(trimmed_q)
        scenarios = await self._scenarios_repo.list_by_states(
            states=[ScenarioState.QUEUED, ScenarioState.IN_REVIEW],
            q=q,
            q_matching_author_user_ids=author_ids_from_name or None,
            category_ids=category_ids,
        )
        portfolio = await portfolio_investigator_ids_for_user(
            user=current_user,
            assignments_repo=self._assignments_repo,
        )
        items: list[ReviewQueueItem] = []
        for scenario in scenarios:
            if UserRole(current_user.role) == UserRole.REVIEWER and not reviewer_has_investigator_in_portfolio(
                user=current_user,
                investigator_user_id=scenario.author_user_id,
                portfolio_investigator_ids=portfolio,
            ):
                continue
            items.append(self._to_queue_item(scenario))
        return items

    async def reviewed_list(
        self,
        *,
        current_user: UserModel,
        q: str | None = None,
        category_ids: list[str] | None = None,
    ) -> list[ReviewedScenarioItem]:
        reviewer_filter: str | None = None
        if UserRole(current_user.role) == UserRole.REVIEWER:
            reviewer_filter = current_user.id or ""
        author_ids_from_name: list[str] | None = None
        trimmed_q = (q or "").strip()
        if trimmed_q:
            author_ids_from_name = await self._users_repo.list_ids_matching_display_name(trimmed_q)
        scenarios = await self._scenarios_repo.list_reviewed(
            reviewer_user_id=reviewer_filter,
            q=q,
            q_matching_author_user_ids=author_ids_from_name or None,
            category_ids=category_ids,
        )
        portfolio = await portfolio_investigator_ids_for_user(
            user=current_user,
            assignments_repo=self._assignments_repo,
        )
        items: list[ReviewedScenarioItem] = []
        for scenario in scenarios:
            if UserRole(current_user.role) == UserRole.REVIEWER and not reviewer_has_investigator_in_portfolio(
                user=current_user,
                investigator_user_id=scenario.author_user_id,
                portfolio_investigator_ids=portfolio,
            ):
                continue
            if scenario.last_reviewed_at is None:
                continue
            live_slug = scenario.public_slug
            items.append(
                ReviewedScenarioItem(
                    scenario_id=scenario.id or "",
                    title=scenario.title,
                    author_user_id=scenario.author_user_id,
                    author_university=scenario.author_university,
                    state=scenario.state,
                    last_reviewed_at=scenario.last_reviewed_at,
                    last_review_outcome=scenario.last_review_outcome,
                    live_public_path=f"/public/{live_slug}" if live_slug else None,
                )
            )
        return items

    async def start_review(self, *, scenario_id: str, current_user: UserModel):
        scenario = await self._require_scenario(scenario_id)
        portfolio = await self._portfolio(current_user)
        if not can_start_review_scenario(
            user=current_user, scenario=scenario, portfolio_investigator_ids=portfolio
        ):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot start review")
        if not is_valid_transition(scenario.state, ScenarioState.IN_REVIEW):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Invalid state transition")
        updated = await self._scenarios_repo.start_review(scenario_id=scenario_id)
        if updated is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")
        await self._record_event(
            scenario_id=updated.id or "",
            event_type=ReviewEventType.REVIEW_STARTED,
            actor=current_user,
            from_state=scenario.state,
            to_state=updated.state,
        )
        return updated, datetime.now(UTC)

    async def request_changes(
        self,
        *,
        scenario_id: str,
        current_user: UserModel,
        note: str,
    ):
        scenario = await self._require_scenario(scenario_id)
        portfolio = await self._portfolio(current_user)
        if not can_request_changes_scenario(
            user=current_user, scenario=scenario, portfolio_investigator_ids=portfolio
        ):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot request changes")
        if not is_valid_transition(scenario.state, ScenarioState.CHANGES_REQUIRED):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Invalid state transition")
        updated = await self._scenarios_repo.request_changes(
            scenario_id=scenario_id,
            reviewer_user_id=current_user.id or "",
            note=note.strip(),
        )
        if updated is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")
        await self._record_event(
            scenario_id=updated.id or "",
            event_type=ReviewEventType.CHANGES_REQUESTED,
            actor=current_user,
            from_state=scenario.state,
            to_state=updated.state,
        )
        await record_scenario_audit(
            self._audit,
            actor=current_user,
            action_type=AuditActionType.SCENARIO_CHANGES_REQUESTED,
            scenario_id=updated.id or "",
            from_state=scenario.state,
            to_state=updated.state,
            current_extra={"note": note.strip()},
        )
        if self._notifications is not None:
            await self._notifications.notify_scenario_changes_required(
                owner_user_id=updated.author_user_id,
                scenario=updated,
                actor_user_id=current_user.id or "",
                note=note,
            )
        return updated, datetime.now(UTC)

    async def mark_not_suitable(
        self,
        *,
        scenario_id: str,
        current_user: UserModel,
        reason: str | None,
    ):
        scenario = await self._require_scenario(scenario_id)
        portfolio = await self._portfolio(current_user)
        if not can_mark_not_suitable_scenario(
            user=current_user, scenario=scenario, portfolio_investigator_ids=portfolio
        ):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot mark as not suitable")
        if not is_valid_transition(scenario.state, ScenarioState.NOT_SUITABLE):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Invalid state transition")
        updated = await self._scenarios_repo.mark_not_suitable(
            scenario_id=scenario_id,
            reviewer_user_id=current_user.id or "",
            reason=reason.strip() if reason else None,
        )
        if updated is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")
        await self._record_event(
            scenario_id=updated.id or "",
            event_type=ReviewEventType.MARKED_NOT_SUITABLE,
            actor=current_user,
            from_state=scenario.state,
            to_state=updated.state,
        )
        extra: dict[str, str] = {}
        if reason:
            extra["reason"] = reason.strip()
        await record_scenario_audit(
            self._audit,
            actor=current_user,
            action_type=AuditActionType.SCENARIO_MARKED_NOT_SUITABLE,
            scenario_id=updated.id or "",
            from_state=scenario.state,
            to_state=updated.state,
            current_extra=extra or None,
        )
        if self._notifications is not None:
            await self._notifications.notify_scenario_not_suitable(
                owner_user_id=updated.author_user_id,
                scenario=updated,
                actor_user_id=current_user.id or "",
                reason=reason,
            )
        return updated, datetime.now(UTC)

    async def reopen(self, *, scenario_id: str, current_user: UserModel):
        scenario = await self._require_scenario(scenario_id)
        if not can_reopen_not_suitable(user=current_user, scenario=scenario):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot reopen scenario")
        if not is_valid_transition(scenario.state, ScenarioState.DRAFT):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Invalid state transition")
        updated = await self._scenarios_repo.reopen_from_not_suitable(scenario_id=scenario_id)
        if updated is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")
        await self._record_event(
            scenario_id=updated.id or "",
            event_type=ReviewEventType.REOPENED_FROM_NOT_SUITABLE,
            actor=current_user,
            from_state=scenario.state,
            to_state=updated.state,
        )
        await record_scenario_audit(
            self._audit,
            actor=current_user,
            action_type=AuditActionType.SCENARIO_REOPENED,
            scenario_id=updated.id or "",
            from_state=scenario.state,
            to_state=updated.state,
        )
        if self._notifications is not None:
            await self._notifications.notify_scenario_reopened(
                owner_user_id=updated.author_user_id,
                scenario=updated,
                actor_user_id=current_user.id or "",
            )
        return updated, datetime.now(UTC)

    async def publish(self, *, scenario_id: str, current_user: UserModel):
        scenario = await self._require_scenario(scenario_id)
        portfolio = await self._portfolio(current_user)
        if not can_publish_scenario(
            user=current_user, scenario=scenario, portfolio_investigator_ids=portfolio
        ):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot publish this scenario")
        if not is_valid_transition(scenario.state, ScenarioState.PUBLISHED):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Invalid state transition")
        if self._suggestions_repo is not None:
            pending = await self._suggestions_repo.count_pending_reviewer_suggestions(
                scenario_id=scenario_id
            )
            if pending > 0:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Resolve pending reviewer suggestions before publishing",
                )
        updated = await self._scenarios_repo.set_state(
            scenario_id=scenario_id,
            state=ScenarioState.PUBLISHED,
            actor_user_id=current_user.id or "",
        )
        if updated is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")
        await self._record_event(
            scenario_id=updated.id or "",
            event_type=ReviewEventType.PUBLISHED,
            actor=current_user,
            from_state=scenario.state,
            to_state=updated.state,
        )
        await record_scenario_audit(
            self._audit,
            actor=current_user,
            action_type=AuditActionType.SCENARIO_PUBLISHED,
            scenario_id=updated.id or "",
            from_state=scenario.state,
            to_state=updated.state,
        )
        if self._notifications is not None:
            await self._notifications.notify_scenario_published(
                owner_user_id=updated.author_user_id,
                scenario=updated,
                actor_user_id=current_user.id or "",
            )
        return updated, datetime.now(UTC)

    def _to_queue_item(self, scenario) -> ReviewQueueItem:
        live_slug = scenario.public_slug
        live_title = scenario.public_title
        live_description = scenario.public_description
        return ReviewQueueItem(
            scenario_id=scenario.id or "",
            title=scenario.title,
            author_user_id=scenario.author_user_id,
            author_university=scenario.author_university,
            state=scenario.state,
            has_prior_approval=scenario.first_approved_at is not None,
            submitted_at=scenario.submitted_for_review_at or scenario.last_state_changed_at,
            live_public_title=live_title,
            live_public_description=live_description,
            live_public_path=f"/public/{live_slug}" if live_slug else None,
        )

    async def _require_scenario(self, scenario_id: str):
        scenario = await self._scenarios_repo.get_by_id(scenario_id)
        if scenario is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")
        return scenario

    async def _portfolio(self, user: UserModel) -> frozenset[str]:
        return await portfolio_investigator_ids_for_user(
            user=user,
            assignments_repo=self._assignments_repo,
        )

    async def _record_event(
        self,
        *,
        scenario_id: str,
        event_type: ReviewEventType,
        actor: UserModel,
        from_state: ScenarioState,
        to_state: ScenarioState,
    ) -> None:
        await self._review_events_repo.create(
            scenario_id=scenario_id,
            event_type=event_type,
            actor_user_id=actor.id or "",
            actor_role=UserRole(actor.role),
            from_state=from_state,
            to_state=to_state,
        )

