"""Mongo repository for persisted AI suggestion decisions."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.domain.enums import UserRole
from app.models.ai_suggestion_decision import AiSuggestionDecisionModel


class AiSuggestionDecisionsRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._collection = db["ai_suggestion_decisions"]

    async def ensure_indexes(self) -> None:
        await self._collection.create_index([("scenario_id", 1), ("created_at", -1)])
        await self._collection.create_index([("actor_user_id", 1), ("created_at", -1)])
        await self._collection.create_index(
            [("scenario_id", 1), ("request_id", 1), ("item_id", 1), ("action", 1)],
            unique=True,
        )

    async def create(
        self,
        *,
        scenario_id: str,
        request_id: str,
        item_id: str,
        action: str,
        scope: str,
        kind: str,
        paragraph_index: int | None,
        current_excerpt: str,
        proposed_text: str,
        rationale: str,
        actor_user_id: str,
        actor_role: UserRole,
    ) -> AiSuggestionDecisionModel:
        await self.ensure_indexes()
        now = datetime.now(UTC)
        doc: dict[str, Any] = {
            "scenario_id": scenario_id,
            "request_id": request_id,
            "item_id": item_id,
            "action": action,
            "scope": scope,
            "kind": kind,
            "paragraph_index": paragraph_index,
            "current_excerpt": current_excerpt.strip(),
            "proposed_text": proposed_text.strip(),
            "rationale": rationale.strip(),
            "actor_user_id": actor_user_id,
            "actor_role": actor_role.value,
            "created_at": now,
        }
        result = await self._collection.insert_one(doc)
        doc["_id"] = str(result.inserted_id)
        return AiSuggestionDecisionModel.model_validate(doc)
