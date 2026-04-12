"""Scenario repository."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.domain.enums import CollaboratorRole, ScenarioState
from app.models.scenario import ScenarioModel


class ScenariosRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._collection = db["scenarios"]

    async def ensure_indexes(self) -> None:
        # Hacemos unico el slug solo cuando es una cadena valida, para no romper
        # con documentos legacy que tienen slug nulo u otros tipos.
        await self._collection.create_index(
            [("slug", 1)],
            unique=True,
            partialFilterExpression={"slug": {"$type": "string"}},
        )
        await self._collection.create_index("author_user_id")
        await self._collection.create_index("collaborators.user_id")
        await self._collection.create_index("state")

    async def create(
        self,
        *,
        slug: str,
        title: str,
        body_markdown: str,
        author_user_id: str,
    ) -> ScenarioModel:
        now = datetime.now(UTC)
        doc = {
            "slug": slug,
            "title": title,
            "body_markdown": body_markdown,
            "author_user_id": author_user_id,
            "collaborators": [
                {
                    "user_id": author_user_id,
                    "role": CollaboratorRole.OWNER.value,
                    "added_at": now,
                    "added_by": author_user_id,
                }
            ],
            "state": ScenarioState.DRAFT.value,
            "current_revision_number": 1,
            "published_at": None,
            "created_at": now,
            "updated_at": now,
        }
        result = await self._collection.insert_one(doc)
        doc["_id"] = str(result.inserted_id)
        return ScenarioModel.model_validate(doc)

    async def get_by_id(self, scenario_id: str) -> ScenarioModel | None:
        if not ObjectId.is_valid(scenario_id):
            return None
        doc = await self._collection.find_one({"_id": ObjectId(scenario_id)})
        return self._to_model(doc)

    async def update_draft_content(
        self,
        *,
        scenario_id: str,
        title: str | None,
        body_markdown: str | None,
    ) -> ScenarioModel | None:
        if not ObjectId.is_valid(scenario_id):
            return None
        set_doc: dict[str, Any] = {"updated_at": datetime.now(UTC)}
        if title is not None:
            set_doc["title"] = title
        if body_markdown is not None:
            set_doc["body_markdown"] = body_markdown
        if len(set_doc) == 1:
            return await self.get_by_id(scenario_id)
        await self._collection.update_one({"_id": ObjectId(scenario_id)}, {"$set": set_doc})
        return await self.get_by_id(scenario_id)

    async def set_state(self, *, scenario_id: str, state: ScenarioState) -> ScenarioModel | None:
        if not ObjectId.is_valid(scenario_id):
            return None
        set_doc: dict[str, Any] = {"state": state.value, "updated_at": datetime.now(UTC)}
        if state == ScenarioState.PUBLISHED:
            set_doc["published_at"] = datetime.now(UTC)
        await self._collection.update_one({"_id": ObjectId(scenario_id)}, {"$set": set_doc})
        return await self.get_by_id(scenario_id)

    async def bump_revision_number(self, *, scenario_id: str) -> ScenarioModel | None:
        if not ObjectId.is_valid(scenario_id):
            return None
        await self._collection.update_one(
            {"_id": ObjectId(scenario_id)},
            {"$inc": {"current_revision_number": 1}, "$set": {"updated_at": datetime.now(UTC)}},
        )
        return await self.get_by_id(scenario_id)

    async def get_by_slug_and_state(self, *, slug: str, state: ScenarioState) -> ScenarioModel | None:
        doc = await self._collection.find_one({"slug": slug, "state": state.value})
        return self._to_model(doc)

    async def replace_collaborators(
        self,
        *,
        scenario_id: str,
        collaborators: list[dict[str, Any]],
    ) -> ScenarioModel | None:
        if not ObjectId.is_valid(scenario_id):
            return None
        await self._collection.update_one(
            {"_id": ObjectId(scenario_id)},
            {"$set": {"collaborators": collaborators, "updated_at": datetime.now(UTC)}},
        )
        return await self.get_by_id(scenario_id)

    async def list_by_state(self, *, state: ScenarioState) -> list[ScenarioModel]:
        items: list[ScenarioModel] = []
        cursor = self._collection.find({"state": state.value}).sort("updated_at", -1)
        async for doc in cursor:
            model = self._to_model(doc)
            if model is not None:
                items.append(model)
        return items

    async def list_for_participating_user(self, *, user_id: str) -> list[ScenarioModel]:
        """Scenarios where the user is author or listed as collaborator."""
        query = {
            "$or": [
                {"author_user_id": user_id},
                {"collaborators.user_id": user_id},
            ]
        }
        items: list[ScenarioModel] = []
        cursor = self._collection.find(query).sort("updated_at", -1)
        async for doc in cursor:
            model = self._to_model(doc)
            if model is not None:
                items.append(model)
        return items

    def _to_model(self, doc: dict[str, Any] | None) -> ScenarioModel | None:
        if doc is None:
            return None
        doc["_id"] = str(doc["_id"])
        return ScenarioModel.model_validate(doc)
