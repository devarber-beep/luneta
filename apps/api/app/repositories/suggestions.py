"""Change suggestions repository."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.domain.enums import ScenarioState, SuggestionStatus, UserRole
from app.models.suggestion import SuggestionModel


class SuggestionsRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._collection = db["suggestions"]

    async def ensure_indexes(self) -> None:
        await self._collection.create_index("scenario_id")
        await self._collection.create_index("author_user_id")
        await self._collection.create_index([("scenario_id", 1), ("status", 1)])

    async def create(
        self,
        *,
        scenario_id: str,
        author_user_id: str,
        author_role: UserRole,
        scope: str,
        kind: str,
        paragraph_index: int | None,
        body: str,
        scenario_state_at_creation: ScenarioState,
    ) -> SuggestionModel:
        now = datetime.now(UTC)
        doc: dict[str, Any] = {
            "scenario_id": scenario_id,
            "author_user_id": author_user_id,
            "author_role": author_role.value,
            "scope": scope,
            "kind": kind,
            "paragraph_index": paragraph_index,
            "body": body.strip(),
            "status": SuggestionStatus.PENDING.value,
            "scenario_state_at_creation": scenario_state_at_creation.value,
            "created_at": now,
            "updated_at": now,
            "resolved_at": None,
            "resolved_by_user_id": None,
        }
        result = await self._collection.insert_one(doc)
        doc["_id"] = str(result.inserted_id)
        return SuggestionModel.model_validate(doc)

    async def get_by_id(self, suggestion_id: str) -> SuggestionModel | None:
        if not ObjectId.is_valid(suggestion_id):
            return None
        doc = await self._collection.find_one({"_id": ObjectId(suggestion_id)})
        return self._to_model(doc)

    async def list_for_scenario(self, *, scenario_id: str) -> list[SuggestionModel]:
        cursor = self._collection.find({"scenario_id": scenario_id}).sort("created_at", 1)
        out: list[SuggestionModel] = []
        async for doc in cursor:
            model = self._to_model(doc)
            if model is not None:
                out.append(model)
        return out

    async def user_has_authored_suggestions(self, *, scenario_id: str, author_user_id: str) -> bool:
        doc = await self._collection.find_one(
            {"scenario_id": scenario_id, "author_user_id": author_user_id},
        )
        return doc is not None

    async def author_has_pending_paragraph_or_scenario_feedback(
        self,
        *,
        scenario_id: str,
        author_user_id: str,
    ) -> bool:
        doc = await self._collection.find_one(
            {
                "scenario_id": scenario_id,
                "author_user_id": author_user_id,
                "status": SuggestionStatus.PENDING.value,
                "scope": {"$in": ["paragraph", "scenario"]},
            }
        )
        return doc is not None

    async def count_pending_reviewer_suggestions(self, *, scenario_id: str) -> int:
        reviewer_roles = [UserRole.REVIEWER.value, UserRole.ADMIN.value]
        count = 0
        cursor = self._collection.find(
            {
                "scenario_id": scenario_id,
                "status": SuggestionStatus.PENDING.value,
                "author_role": {"$in": reviewer_roles},
            }
        )
        async for _ in cursor:
            count += 1
        return count

    async def set_status(
        self,
        *,
        suggestion_id: str,
        status: SuggestionStatus,
        resolved_by_user_id: str,
    ) -> SuggestionModel | None:
        if not ObjectId.is_valid(suggestion_id):
            return None
        now = datetime.now(UTC)
        await self._collection.update_one(
            {"_id": ObjectId(suggestion_id)},
            {
                "$set": {
                    "status": status.value,
                    "resolved_at": now,
                    "resolved_by_user_id": resolved_by_user_id,
                    "updated_at": now,
                }
            },
        )
        return await self.get_by_id(suggestion_id)

    async def mark_applied(self, *, suggestion_id: str) -> SuggestionModel | None:
        if not ObjectId.is_valid(suggestion_id):
            return None
        now = datetime.now(UTC)
        await self._collection.update_one(
            {"_id": ObjectId(suggestion_id)},
            {"$set": {"applied_at": now, "updated_at": now}},
        )
        return await self.get_by_id(suggestion_id)

    def _to_model(self, doc: dict[str, Any] | None) -> SuggestionModel | None:
        if doc is None:
            return None
        out = dict(doc)
        out["_id"] = str(out["_id"])
        return SuggestionModel.model_validate(out)
