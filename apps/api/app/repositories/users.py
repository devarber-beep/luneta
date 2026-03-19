"""Users repository."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.user import UserModel


class UsersRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._collection = db["users"]

    async def ensure_indexes(self) -> None:
        await self._collection.create_index("email", unique=True)

    async def create(self, *, email: str, password_hash: str, role: str) -> UserModel:
        now = datetime.now(UTC)
        doc = {
            "email": email,
            "password_hash": password_hash,
            "role": role,
            "is_email_verified": False,
            "created_at": now,
            "updated_at": now,
        }
        result = await self._collection.insert_one(doc)
        doc["_id"] = str(result.inserted_id)
        return UserModel.model_validate(doc)

    async def get_by_email(self, email: str) -> UserModel | None:
        doc = await self._collection.find_one({"email": email})
        return self._to_model(doc)

    async def get_by_id(self, user_id: str) -> UserModel | None:
        if not ObjectId.is_valid(user_id):
            return None
        doc = await self._collection.find_one({"_id": ObjectId(user_id)})
        return self._to_model(doc)

    async def mark_email_verified(self, user_id: str) -> bool:
        if not ObjectId.is_valid(user_id):
            return False
        result = await self._collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"is_email_verified": True, "updated_at": datetime.now(UTC)}},
        )
        return result.modified_count == 1

    def _to_model(self, doc: dict[str, Any] | None) -> UserModel | None:
        if doc is None:
            return None
        doc["_id"] = str(doc["_id"])
        return UserModel.model_validate(doc)
