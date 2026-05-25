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
        await self._collection.create_index([("scenario_id", 1), ("actor_user_id", 1), ("event_type", 1)])

    async def actor_has_reviewed_scenario(self, *, scenario_id: str, actor_user_id: str) -> bool:
        """True if this user completed a substantive review action on the scenario."""
        substantive = [
            ReviewEventType.PUBLISHED.value,
            ReviewEventType.CHANGES_REQUESTED.value,
            ReviewEventType.MARKED_NOT_SUITABLE.value,
        ]
        doc = await self._collection.find_one(
            {
                "scenario_id": scenario_id,
                "actor_user_id": actor_user_id,
                "event_type": {"$in": substantive},
            }
        )
        return doc is not None

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
