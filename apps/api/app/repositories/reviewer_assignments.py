"""Reviewer portfolio assignments."""
from __future__ import annotations

from datetime import UTC, datetime

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.errors import DuplicateKeyError

from app.models.reviewer_assignment import ReviewerAssignmentModel


class ReviewerAssignmentsRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._collection = db["reviewer_assignments"]

    async def ensure_indexes(self) -> None:
        await self._collection.create_index(
            [("reviewer_user_id", 1), ("investigator_user_id", 1)],
            unique=True,
        )
        await self._collection.create_index([("investigator_user_id", 1)])

    async def assign(self, *, reviewer_user_id: str, investigator_user_id: str) -> ReviewerAssignmentModel:
        now = datetime.now(UTC)
        doc = {
            "reviewer_user_id": reviewer_user_id,
            "investigator_user_id": investigator_user_id,
            "created_at": now,
        }
        try:
            result = await self._collection.insert_one(doc)
        except DuplicateKeyError:
            existing = await self._collection.find_one(
                {
                    "reviewer_user_id": reviewer_user_id,
                    "investigator_user_id": investigator_user_id,
                }
            )
            if existing is None:
                raise
            doc = existing
            doc["_id"] = str(doc["_id"])
            return ReviewerAssignmentModel.model_validate(doc)
        doc["_id"] = str(result.inserted_id)
        return ReviewerAssignmentModel.model_validate(doc)

    async def remove(self, *, reviewer_user_id: str, investigator_user_id: str) -> bool:
        result = await self._collection.delete_one(
            {
                "reviewer_user_id": reviewer_user_id,
                "investigator_user_id": investigator_user_id,
            }
        )
        return result.deleted_count > 0

    async def list_investigator_ids_for_reviewer(self, reviewer_user_id: str) -> list[str]:
        cursor = self._collection.find({"reviewer_user_id": reviewer_user_id}, {"investigator_user_id": 1})
        ids: list[str] = []
        async for doc in cursor:
            inv = doc.get("investigator_user_id")
            if isinstance(inv, str):
                ids.append(inv)
        return ids

    async def is_assigned(self, *, reviewer_user_id: str, investigator_user_id: str) -> bool:
        doc = await self._collection.find_one(
            {
                "reviewer_user_id": reviewer_user_id,
                "investigator_user_id": investigator_user_id,
            }
        )
        return doc is not None
