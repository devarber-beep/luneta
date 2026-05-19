"""Scenario revisions repository."""
from __future__ import annotations

from datetime import UTC, datetime

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.domain.enums import ScenarioState
from app.models.scenario_revision import ScenarioRevisionModel


class ScenarioRevisionsRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._collection = db["scenario_revisions"]

    async def ensure_indexes(self) -> None:
        await self._collection.create_index(
            [("scenario_id", 1), ("revision_number", -1)],
            unique=True,
        )

    async def create_snapshot(
        self,
        *,
        scenario_id: str,
        revision_number: int,
        title: str,
        description: str,
        state_snapshot: ScenarioState,
        created_by_user_id: str,
    ) -> ScenarioRevisionModel:
        doc = {
            "scenario_id": scenario_id,
            "revision_number": revision_number,
            "title": title,
            "description": description,
            "state_snapshot": state_snapshot.value,
            "created_by_user_id": created_by_user_id,
            "created_at": datetime.now(UTC),
        }
        result = await self._collection.insert_one(doc)
        doc["_id"] = str(result.inserted_id)
        return ScenarioRevisionModel.model_validate(doc)
