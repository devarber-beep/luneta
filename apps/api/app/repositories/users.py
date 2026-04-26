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
        await self._collection.create_index("email_normalized", unique=True)
        await self._collection.create_index("nickname", unique=True)
        await self._collection.create_index("nickname_normalized", unique=True)

    async def create(
        self,
        *,
        email: str,
        password_hash: str,
        role: str,
        nickname: str,
        first_name: str | None = None,
        last_name: str | None = None,
    ) -> UserModel:
        now = datetime.now(UTC)
        email_normalized = email.strip().lower()
        nickname_normalized = nickname.strip().lower()
        doc = {
            "email": email,
            "email_normalized": email_normalized,
            "password_hash": password_hash,
            "password_updated_at": now,
            "role": role,
            "is_email_verified": False,
            "email_verified_at": None,
            "nickname": nickname,
            "nickname_normalized": nickname_normalized,
            "first_name": first_name,
            "last_name": last_name,
            "avatar": None,
            "last_login_at": None,
            "created_at": now,
            "updated_at": now,
        }
        result = await self._collection.insert_one(doc)
        doc["_id"] = str(result.inserted_id)
        return UserModel.model_validate(doc)

    async def get_by_email(self, email: str) -> UserModel | None:
        normalized = email.strip().lower()
        doc = await self._collection.find_one({"email_normalized": normalized})
        return self._to_model(doc)

    async def get_by_nickname(self, nickname: str) -> UserModel | None:
        normalized = nickname.strip().lower()
        doc = await self._collection.find_one({"nickname_normalized": normalized})
        return self._to_model(doc)

    async def get_by_id(self, user_id: str) -> UserModel | None:
        if not ObjectId.is_valid(user_id):
            return None
        doc = await self._collection.find_one({"_id": ObjectId(user_id)})
        return self._to_model(doc)

    async def get_by_ids(self, user_ids: list[str]) -> dict[str, UserModel]:
        oids: list[ObjectId] = []
        for uid in dict.fromkeys(user_ids):
            if ObjectId.is_valid(uid):
                oids.append(ObjectId(uid))
        if not oids:
            return {}
        out: dict[str, UserModel] = {}
        cursor = self._collection.find({"_id": {"$in": oids}})
        async for doc in cursor:
            model = self._to_model(doc)
            if model is not None and model.id is not None:
                out[model.id] = model
        return out

    async def map_display_names(self, user_ids: list[str]) -> dict[str, str]:
        users = await self.get_by_ids(user_ids)
        return {uid: u.nickname for uid, u in users.items()}

    async def list_verified_emails_by_role(self, role: str) -> list[str]:
        cursor = self._collection.find(
            {"role": role, "is_email_verified": True},
            {"email": 1, "_id": 0},
        )
        out: list[str] = []
        async for doc in cursor:
            email = doc.get("email")
            if isinstance(email, str) and email:
                out.append(email)
        return out

    async def touch_last_login(self, user_id: str) -> None:
        if not ObjectId.is_valid(user_id):
            return
        await self._collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"last_login_at": datetime.now(UTC), "updated_at": datetime.now(UTC)}},
        )

    async def mark_email_verified(self, user_id: str) -> bool:
        if not ObjectId.is_valid(user_id):
            return False
        result = await self._collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"is_email_verified": True, "email_verified_at": datetime.now(UTC), "updated_at": datetime.now(UTC)}},
        )
        return result.modified_count == 1

    async def update_profile(
        self,
        user_id: str,
        *,
        nickname: str,
        first_name: str | None,
        last_name: str | None,
    ) -> UserModel | None:
        if not ObjectId.is_valid(user_id):
            return None
        nick = nickname.strip()
        now = datetime.now(UTC)
        await self._collection.update_one(
            {"_id": ObjectId(user_id)},
            {
                "$set": {
                    "nickname": nick,
                    "nickname_normalized": nick.lower(),
                    "first_name": first_name,
                    "last_name": last_name,
                    "updated_at": now,
                }
            },
        )
        doc = await self._collection.find_one({"_id": ObjectId(user_id)})
        return self._to_model(doc)

    async def set_password_hash(self, user_id: str, *, password_hash: str) -> UserModel | None:
        if not ObjectId.is_valid(user_id):
            return None
        now = datetime.now(UTC)
        result = await self._collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"password_hash": password_hash, "password_updated_at": now, "updated_at": now}},
        )
        if result.matched_count == 0:
            return None
        doc = await self._collection.find_one({"_id": ObjectId(user_id)})
        return self._to_model(doc)

    def _to_model(self, doc: dict[str, Any] | None) -> UserModel | None:
        if doc is None:
            return None
        doc["_id"] = str(doc["_id"])
        return UserModel.model_validate(doc)
