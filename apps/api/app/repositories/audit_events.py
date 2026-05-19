"""Audit events repository."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.domain.enums import AuditActionType, AuditSubjectType, UserRole
from app.models.audit_event import AuditEventModel


class AuditEventsRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._collection = db["audit_events"]

    async def ensure_indexes(self) -> None:
        await self._collection.create_index([("created_at", -1)])
        await self._collection.create_index([("actor_user_id", 1), ("created_at", -1)])
        await self._collection.create_index([("action_type", 1), ("created_at", -1)])
        await self._collection.create_index(
            [("subject_type", 1), ("subject_id", 1), ("created_at", -1)]
        )

    async def create(
        self,
        *,
        actor_user_id: str,
        actor_role: UserRole,
        action_type: AuditActionType,
        subject_type: AuditSubjectType,
        subject_id: str,
        previous: dict[str, Any] | None = None,
        current: dict[str, Any] | None = None,
    ) -> AuditEventModel:
        now = datetime.now(UTC)
        doc = {
            "actor_user_id": actor_user_id,
            "actor_role": actor_role.value,
            "action_type": action_type.value,
            "subject_type": subject_type.value,
            "subject_id": subject_id,
            "previous": previous,
            "current": current,
            "created_at": now,
        }
        result = await self._collection.insert_one(doc)
        doc["_id"] = str(result.inserted_id)
        return AuditEventModel.model_validate(doc)
