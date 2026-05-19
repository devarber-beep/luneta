"""Review event repository."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.domain.enums import ReviewEventType, ScenarioState, UserRole
from app.models.review_event import ReviewEventModel


class ReviewEventsRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._collection = db["review_events"]

    async def ensure_indexes(self) -> None:
        await self._collection.create_index([("scenario_id", 1), ("created_at", -1)])

    async def create(
        self,
        *,
        scenario_id: str,
        event_type: ReviewEventType,
        actor_user_id: str,
        actor_role: UserRole,
        from_state: ScenarioState | None = None,
        to_state: ScenarioState | None = None,
    ) -> ReviewEventModel:
        doc: dict[str, Any] = {
            "scenario_id": scenario_id,
            "event_type": event_type.value,
            "actor_user_id": actor_user_id,
            "actor_role": actor_role.value,
            "created_at": datetime.now(UTC),
        }
        if from_state is not None:
            doc["from_state"] = from_state.value
        if to_state is not None:
            doc["to_state"] = to_state.value
        result = await self._collection.insert_one(doc)
        doc["_id"] = str(result.inserted_id)
        return ReviewEventModel.model_validate(doc)
