"""Audit trail: writes on platform actions and admin read queries."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import HTTPException, status

from app.domain.enums import AuditActionType, AuditSubjectType, UserRole
from app.models.audit_event import AuditEventModel
from app.models.user import UserModel
from app.repositories.audit_events import AuditEventsRepository
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
        actor_user_id: str | None = None,
        action_types: list[AuditActionType] | None = None,
        subject_type: AuditSubjectType | None = None,
        subject_id: str | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[AuditEventModel], int]:
        safe_page = max(1, page)
        safe_size = min(max(1, page_size), 100)
        return await self._audit_repo.list_filtered(
            actor_user_id=actor_user_id,
            action_types=action_types,
            subject_type=subject_type,
            subject_id=subject_id,
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
    ) -> None:
        self._audit = AuditService(audit_repo=audit_repo)
        self._users_repo = users_repo

    async def get_event_detail(self, *, event_id: str) -> dict[str, Any]:
        event = await self._audit.get_event(event_id=event_id)
        return (await self._enrich([event]))[0]

    async def list_events_enriched(
        self,
        *,
        actor_user_id: str | None = None,
        action_types: list[AuditActionType] | None = None,
        subject_type: AuditSubjectType | None = None,
        subject_id: str | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[dict[str, Any]], int]:
        events, total = await self._audit.list_events(
            actor_user_id=actor_user_id,
            action_types=action_types,
            subject_type=subject_type,
            subject_id=subject_id,
            created_from=created_from,
            created_to=created_to,
            page=page,
            page_size=page_size,
        )
        return await self._enrich(events), total

    async def _enrich(self, events: list[AuditEventModel]) -> list[dict[str, Any]]:
        actor_ids = {event.actor_user_id for event in events if event.actor_user_id}
        users = await self._users_repo.get_by_ids(list(actor_ids))
        rows: list[dict[str, Any]] = []
        for event in events:
            actor = users.get(event.actor_user_id)
            rows.append(
                {
                    "id": event.id or "",
                    "actor_user_id": event.actor_user_id,
                    "actor_nickname": actor.nickname if actor else None,
                    "actor_email_normalized": actor.email_normalized if actor else None,
                    "actor_role": event.actor_role.value,
                    "action_type": event.action_type.value,
                    "subject_type": event.subject_type.value,
                    "subject_id": event.subject_id,
                    "previous": event.previous,
                    "current": event.current,
                    "created_at": event.created_at,
                }
            )
        return rows
