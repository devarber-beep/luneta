"""User notifications repository (in-app channel)."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.domain.enums import NotificationEntityType, NotificationType
from app.models.notification import NotificationModel


class NotificationsRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._collection = db["notifications"]

    async def ensure_indexes(self) -> None:
        await self._collection.create_index(
            [("recipient_user_id", 1), ("created_at", -1)],
        )
        await self._collection.create_index(
            [("recipient_user_id", 1), ("read_at", 1), ("created_at", -1)],
        )

    async def create(
        self,
        *,
        recipient_user_id: str,
        notification_type: NotificationType,
        title: str,
        entity_type: NotificationEntityType,
        entity_id: str,
        message: str | None = None,
        scenario_id: str | None = None,
        actor_user_id: str | None = None,
        link_path: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> NotificationModel:
        now = datetime.now(UTC)
        doc: dict[str, Any] = {
            "recipient_user_id": recipient_user_id,
            "notification_type": notification_type.value,
            "title": title.strip(),
            "message": message.strip() if message else None,
            "entity_type": entity_type.value,
            "entity_id": entity_id,
            "scenario_id": scenario_id,
            "actor_user_id": actor_user_id,
            "link_path": link_path,
            "payload": payload,
            "read_at": None,
            "created_at": now,
        }
        result = await self._collection.insert_one(doc)
        doc["_id"] = str(result.inserted_id)
        return NotificationModel.model_validate(doc)

    async def get_by_id_for_recipient(
        self,
        *,
        notification_id: str,
        recipient_user_id: str,
    ) -> NotificationModel | None:
        if not ObjectId.is_valid(notification_id):
            return None
        doc = await self._collection.find_one(
            {
                "_id": ObjectId(notification_id),
                "recipient_user_id": recipient_user_id,
            }
        )
        return self._to_model(doc)

    async def list_for_recipient(
        self,
        *,
        recipient_user_id: str,
        unread_only: bool = False,
        page: int = 1,
        page_size: int = 30,
    ) -> tuple[list[NotificationModel], int]:
        query: dict[str, Any] = {"recipient_user_id": recipient_user_id}
        if unread_only:
            query["read_at"] = None

        total = await self._collection.count_documents(query)
        skip = max(0, (page - 1) * page_size)
        cursor = (
            self._collection.find(query)
            .sort("created_at", -1)
            .skip(skip)
            .limit(page_size)
        )
        items: list[NotificationModel] = []
        async for doc in cursor:
            model = self._to_model(doc)
            if model is not None:
                items.append(model)
        return items, total

    async def count_unread(self, *, recipient_user_id: str) -> int:
        return await self._collection.count_documents(
            {"recipient_user_id": recipient_user_id, "read_at": None}
        )

    async def mark_read(
        self,
        *,
        notification_id: str,
        recipient_user_id: str,
    ) -> NotificationModel | None:
        if not ObjectId.is_valid(notification_id):
            return None
        existing = await self.get_by_id_for_recipient(
            notification_id=notification_id,
            recipient_user_id=recipient_user_id,
        )
        if existing is None or existing.read_at is not None:
            return None
        now = datetime.now(UTC)
        await self._collection.update_one(
            {
                "_id": ObjectId(notification_id),
                "recipient_user_id": recipient_user_id,
            },
            {"$set": {"read_at": now}},
        )
        return await self.get_by_id_for_recipient(
            notification_id=notification_id,
            recipient_user_id=recipient_user_id,
        )

    async def mark_all_read(self, *, recipient_user_id: str) -> int:
        now = datetime.now(UTC)
        update = await self._collection.update_many(
            {"recipient_user_id": recipient_user_id, "read_at": None},
            {"$set": {"read_at": now}},
        )
        return update.modified_count

    @staticmethod
    def _to_model(doc: dict[str, Any] | None) -> NotificationModel | None:
        if doc is None:
            return None
        doc = dict(doc)
        doc["_id"] = str(doc["_id"])
        return NotificationModel.model_validate(doc)
