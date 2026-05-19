"""Flat scenario category catalog."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.scenario_classification import ScenarioClassificationEntryModel


class ScenarioClassificationRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._collection = db["scenario_classification_catalog"]

    async def ensure_indexes(self) -> None:
        await self._collection.create_index("slug", unique=True)
        await self._collection.create_index([("sort_order", 1)])

    async def upsert_seed_entry(
        self,
        *,
        slug: str,
        label: str,
        sort_order: int,
    ) -> ScenarioClassificationEntryModel:
        now = datetime.now(UTC)
        existing = await self._collection.find_one({"slug": slug})
        if existing is None:
            doc: dict[str, Any] = {
                "slug": slug,
                "label": label,
                "is_active": True,
                "sort_order": sort_order,
                "created_at": now,
                "updated_at": now,
            }
            result = await self._collection.insert_one(doc)
            doc["_id"] = str(result.inserted_id)
        else:
            doc_id = existing["_id"]
            await self._collection.update_one(
                {"_id": doc_id},
                {
                    "$set": {
                        "label": label,
                        "is_active": True,
                        "sort_order": sort_order,
                        "updated_at": now,
                    }
                },
            )
            doc = await self._collection.find_one({"_id": doc_id})
        return self._to_model(doc)

    async def list_active(self) -> list[ScenarioClassificationEntryModel]:
        cursor = self._collection.find({"is_active": True}).sort("sort_order", 1)
        out: list[ScenarioClassificationEntryModel] = []
        async for doc in cursor:
            model = self._to_model(doc)
            if model is not None:
                out.append(model)
        return out

    async def get_by_id(self, entry_id: str) -> ScenarioClassificationEntryModel | None:
        if not ObjectId.is_valid(entry_id):
            return None
        doc = await self._collection.find_one({"_id": ObjectId(entry_id)})
        return self._to_model(doc)

    async def get_by_slug(self, slug: str) -> ScenarioClassificationEntryModel | None:
        doc = await self._collection.find_one({"slug": slug.strip().lower()})
        return self._to_model(doc)

    async def list_all(self) -> list[ScenarioClassificationEntryModel]:
        cursor = self._collection.find({}).sort("sort_order", 1)
        out: list[ScenarioClassificationEntryModel] = []
        async for doc in cursor:
            model = self._to_model(doc)
            if model is not None:
                out.append(model)
        return out

    async def create_entry(
        self,
        *,
        slug: str,
        label: str,
        sort_order: int,
    ) -> ScenarioClassificationEntryModel:
        now = datetime.now(UTC)
        doc: dict[str, Any] = {
            "slug": slug.strip().lower(),
            "label": label.strip(),
            "is_active": True,
            "sort_order": sort_order,
            "created_at": now,
            "updated_at": now,
        }
        result = await self._collection.insert_one(doc)
        doc["_id"] = result.inserted_id
        return self._to_model(doc)

    async def update_entry(
        self,
        entry_id: str,
        *,
        label: str | None = None,
        sort_order: int | None = None,
        is_active: bool | None = None,
    ) -> ScenarioClassificationEntryModel | None:
        if not ObjectId.is_valid(entry_id):
            return None
        updates: dict[str, Any] = {"updated_at": datetime.now(UTC)}
        if label is not None:
            updates["label"] = label.strip()
        if sort_order is not None:
            updates["sort_order"] = sort_order
        if is_active is not None:
            updates["is_active"] = is_active
        result = await self._collection.update_one({"_id": ObjectId(entry_id)}, {"$set": updates})
        if result.matched_count == 0:
            return None
        doc = await self._collection.find_one({"_id": ObjectId(entry_id)})
        return self._to_model(doc)

    def _to_model(self, doc: dict[str, Any] | None) -> ScenarioClassificationEntryModel | None:
        if doc is None:
            return None
        doc = dict(doc)
        doc["_id"] = str(doc["_id"])
        return ScenarioClassificationEntryModel.model_validate(doc)
