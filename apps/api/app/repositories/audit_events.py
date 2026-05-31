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

    async def get_by_id(self, event_id: str) -> AuditEventModel | None:
        try:
            oid = ObjectId(event_id)
        except Exception:
            return None
        doc = await self._collection.find_one({"_id": oid})
        if doc is None:
            return None
        doc["_id"] = str(doc["_id"])
        return AuditEventModel.model_validate(doc)

    async def list_filtered(
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
        await self.ensure_indexes()
        query: dict[str, Any] = {}
        if actor_user_id:
            query["actor_user_id"] = actor_user_id
        if action_types:
            values = [item.value for item in action_types]
            query["action_type"] = values[0] if len(values) == 1 else {"$in": values}
        if subject_type is not None:
            query["subject_type"] = subject_type.value
        if subject_id:
            query["subject_id"] = subject_id
        if created_from is not None or created_to is not None:
            created_filter: dict[str, Any] = {}
            if created_from is not None:
                created_filter["$gte"] = created_from
            if created_to is not None:
                created_filter["$lte"] = created_to
            query["created_at"] = created_filter

        total = await self._collection.count_documents(query)
        skip = max(0, (page - 1) * page_size)
        cursor = self._collection.find(query).sort("created_at", -1).skip(skip).limit(page_size)
        items: list[AuditEventModel] = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            items.append(AuditEventModel.model_validate(doc))
        return items, total
