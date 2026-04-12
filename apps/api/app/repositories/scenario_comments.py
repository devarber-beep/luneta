"""Scenario comments repository."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.scenario_comment import ScenarioCommentModel


class ScenarioCommentsRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._collection = db["scenario_comments"]

    async def ensure_indexes(self) -> None:
        await self._collection.create_index([("scenario_id", 1), ("created_at", -1)])

    async def create(
        self,
        *,
        scenario_id: str,
        author_user_id: str,
        body_markdown: str,
        revision_number: int | None,
        section_key: str | None,
        field_path: str | None,
    ) -> ScenarioCommentModel:
        now = datetime.now(UTC)
        doc: dict[str, Any] = {
            "scenario_id": scenario_id,
            "author_user_id": author_user_id,
            "body_markdown": body_markdown,
            "revision_number": revision_number,
            "section_key": section_key,
            "field_path": field_path,
            "created_at": now,
            "updated_at": now,
        }
        result = await self._collection.insert_one(doc)
        doc["_id"] = str(result.inserted_id)
        return ScenarioCommentModel.model_validate(doc)

    async def list_by_scenario_id(self, *, scenario_id: str) -> list[ScenarioCommentModel]:
        items: list[ScenarioCommentModel] = []
        cursor = self._collection.find({"scenario_id": scenario_id}).sort("created_at", 1)
        async for doc in cursor:
            model = self._to_model(doc)
            if model is not None:
                items.append(model)
        return items

    async def get_by_id(self, comment_id: str) -> ScenarioCommentModel | None:
        if not ObjectId.is_valid(comment_id):
            return None
        doc = await self._collection.find_one({"_id": ObjectId(comment_id)})
        return self._to_model(doc)

    def _to_model(self, doc: dict[str, Any] | None) -> ScenarioCommentModel | None:
        if doc is None:
            return None
        doc["_id"] = str(doc["_id"])
        return ScenarioCommentModel.model_validate(doc)
