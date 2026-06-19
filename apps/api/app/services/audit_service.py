"""Audit trail: writes on platform actions and admin read queries."""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from fastapi import HTTPException, status

from app.domain.enums import AuditActionType, AuditSubjectType, UserRole
from app.models.audit_event import AuditEventModel
from app.models.user import UserModel
from app.repositories.audit_events import AuditEventsRepository
from app.repositories.scenarios import ScenariosRepository
from app.repositories.users import UsersRepository


class AuditService:
    def __init__(self, *, audit_repo: AuditEventsRepository) -> None:
        self._audit_repo = audit_repo

    async def record(
        self,
        *,
        actor: UserModel,
        action_type: AuditActionType,
        subject_type: AuditSubjectType,
        subject_id: str,
        previous: dict[str, Any] | None = None,
        current: dict[str, Any] | None = None,
    ) -> AuditEventModel:
        await self._audit_repo.ensure_indexes()
        return await self._audit_repo.create(
            actor_user_id=actor.id or "",
            actor_role=UserRole(actor.role),
            action_type=action_type,
            subject_type=subject_type,
            subject_id=subject_id,
            previous=previous,
            current=current,
        )

    async def get_event(self, *, event_id: str) -> AuditEventModel:
        event = await self._audit_repo.get_by_id(event_id)
        if event is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit event not found")
        return event

    async def count_for_actor_since(
        self,
        *,
        actor_user_id: str,
        action_type: AuditActionType,
        since: datetime,
    ) -> int:
        return await self._audit_repo.count_for_actor_since(
            actor_user_id=actor_user_id,
            action_type=action_type,
            since=since,
        )

    async def list_events(
        self,
        *,
        actor_user_ids: list[str] | None = None,
        action_types: list[AuditActionType] | None = None,
        subject_type: AuditSubjectType | None = None,
        subject_ids: list[str] | None = None,
        subject_clauses: list[dict[str, Any]] | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[AuditEventModel], int]:
        safe_page = max(1, page)
        safe_size = min(max(1, page_size), 100)
        return await self._audit_repo.list_filtered(
            actor_user_ids=actor_user_ids,
            action_types=action_types,
            subject_type=subject_type,
            subject_ids=subject_ids,
            subject_clauses=subject_clauses,
            created_from=created_from,
            created_to=created_to,
            page=safe_page,
            page_size=safe_size,
        )


class AuditQueryService:
    """Enriches audit rows with actor profile fields for admin UI."""

    def __init__(
        self,
        *,
        audit_repo: AuditEventsRepository,
        users_repo: UsersRepository,
        scenarios_repo: ScenariosRepository,
    ) -> None:
        self._audit = AuditService(audit_repo=audit_repo)
        self._users_repo = users_repo
        self._scenarios_repo = scenarios_repo

    async def get_event_detail(self, *, event_id: str) -> dict[str, Any]:
        event = await self._audit.get_event(event_id=event_id)
        return (await self._enrich([event]))[0]

    async def list_events_enriched(
        self,
        *,
        actor_query: str | None = None,
        action_types: list[AuditActionType] | None = None,
        subject_type: AuditSubjectType | None = None,
        subject_query: str | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[dict[str, Any]], int]:
        actor_user_ids = await self._resolve_actor_user_ids(actor_query)
        if actor_user_ids is not None and not actor_user_ids:
            return [], 0

        subject_ids, subject_clauses = await self._resolve_subject_filters(
            subject_query=subject_query,
            subject_type=subject_type,
        )
        if subject_ids is not None and not subject_ids:
            return [], 0
        if subject_clauses is not None and not subject_clauses:
            return [], 0

        events, total = await self._audit.list_events(
            actor_user_ids=actor_user_ids,
            action_types=action_types,
            subject_type=subject_type,
            subject_ids=subject_ids,
            subject_clauses=subject_clauses,
            created_from=created_from,
            created_to=created_to,
            page=page,
            page_size=page_size,
        )
        return await self._enrich(events), total

    async def _resolve_actor_user_ids(self, actor_query: str | None) -> list[str] | None:
        trimmed = (actor_query or "").strip()
        if not trimmed:
            return None
        users = await self._users_repo.list_for_admin_summary(q=trimmed, include_disabled=True)
        return [user.id for user in users if user.id]

    async def _resolve_subject_filters(
        self,
        *,
        subject_query: str | None,
        subject_type: AuditSubjectType | None,
    ) -> tuple[list[str] | None, list[dict[str, Any]] | None]:
        trimmed = (subject_query or "").strip()
        if not trimmed:
            return None, None

        if subject_type == AuditSubjectType.USER:
            user_ids = await self._resolve_actor_user_ids(trimmed)
            return user_ids, None

        if subject_type == AuditSubjectType.SCENARIO:
            scenario_ids = await self._scenarios_repo.list_ids_matching_title(trimmed)
            return scenario_ids, None

        if subject_type is None:
            user_ids = await self._resolve_actor_user_ids(trimmed) or []
            scenario_ids = await self._scenarios_repo.list_ids_matching_title(trimmed)
            clauses: list[dict[str, Any]] = []
            if user_ids:
                clauses.append({"subject_type": AuditSubjectType.USER.value, "subject_id": {"$in": user_ids}})
            if scenario_ids:
                clauses.append(
                    {"subject_type": AuditSubjectType.SCENARIO.value, "subject_id": {"$in": scenario_ids}}
                )
            return None, clauses

        pattern = re.escape(trimmed)
        return None, [{"subject_id": {"$regex": pattern, "$options": "i"}}]

    async def _enrich(self, events: list[AuditEventModel]) -> list[dict[str, Any]]:
        actor_ids = {event.actor_user_id for event in events if event.actor_user_id}
        users = await self._users_repo.get_by_ids(list(actor_ids))
        subject_user_ids = {
            event.subject_id
            for event in events
            if event.subject_type == AuditSubjectType.USER and event.subject_id
        }
        subject_users = await self._users_repo.get_by_ids(list(subject_user_ids))
        subject_scenario_ids = {
            event.subject_id
            for event in events
            if event.subject_type == AuditSubjectType.SCENARIO and event.subject_id
        }
        subject_scenarios = await self._scenarios_repo.map_titles_by_ids(list(subject_scenario_ids))

        rows: list[dict[str, Any]] = []
        for event in events:
            actor = users.get(event.actor_user_id)
            subject_label: str | None = None
            if event.subject_type == AuditSubjectType.USER:
                subject_user = subject_users.get(event.subject_id)
                if subject_user:
                    subject_label = f"{subject_user.display_name} ({subject_user.email_normalized})"
            elif event.subject_type == AuditSubjectType.SCENARIO:
                title = subject_scenarios.get(event.subject_id)
                if title:
                    subject_label = title

            rows.append(
                {
                    "id": event.id or "",
                    "actor_user_id": event.actor_user_id,
                    "actor_display_name": actor.display_name if actor else None,
                    "actor_email_normalized": actor.email_normalized if actor else None,
                    "actor_role": event.actor_role.value,
                    "action_type": event.action_type.value,
                    "subject_type": event.subject_type.value,
                    "subject_id": event.subject_id,
                    "subject_display_label": subject_label,
                    "previous": event.previous,
                    "current": event.current,
                    "created_at": event.created_at,
                }
            )
        return rows
