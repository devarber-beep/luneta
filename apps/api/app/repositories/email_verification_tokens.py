"""Email verification token repository."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.email_verification_token import EmailVerificationTokenModel


class EmailVerificationTokensRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._collection = db["email_verification_tokens"]

    async def ensure_indexes(self) -> None:
        await self._collection.create_index("token_hash", unique=True)
        await self._collection.create_index("expires_at")

    async def create(
        self,
        *,
        user_id: str,
        email: str,
        token_hash: str,
        expires_at: datetime,
    ) -> EmailVerificationTokenModel:
        doc = {
            "user_id": user_id,
            "email": email,
            "token_hash": token_hash,
            "expires_at": expires_at,
            "consumed_at": None,
            "created_at": datetime.now(UTC),
        }
        result = await self._collection.insert_one(doc)
        doc["_id"] = str(result.inserted_id)
        return EmailVerificationTokenModel.model_validate(doc)

    async def get_active_by_token_hash(self, token_hash: str) -> EmailVerificationTokenModel | None:
        now = datetime.now(UTC)
        doc = await self._collection.find_one(
            {
                "token_hash": token_hash,
                "consumed_at": None,
                "expires_at": {"$gt": now},
            }
        )
        return self._to_model(doc)

    async def consume(self, token_id: str) -> bool:
        if not ObjectId.is_valid(token_id):
            return False
        result = await self._collection.update_one(
            {"_id": ObjectId(token_id), "consumed_at": None},
            {"$set": {"consumed_at": datetime.now(UTC)}},
        )
        return result.modified_count == 1

    def _to_model(self, doc: dict[str, Any] | None) -> EmailVerificationTokenModel | None:
        if doc is None:
            return None
        doc["_id"] = str(doc["_id"])
        return EmailVerificationTokenModel.model_validate(doc)
