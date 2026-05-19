"""Write-side audit trail for administrative and platform actions."""
from __future__ import annotations

from typing import Any

from app.domain.enums import AuditActionType, AuditSubjectType, UserRole
from app.models.audit_event import AuditEventModel
from app.models.user import UserModel
from app.repositories.audit_events import AuditEventsRepository


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
