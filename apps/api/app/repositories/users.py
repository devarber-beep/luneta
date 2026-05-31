"""Users repository."""
from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.domain.enums import UserAccountStatus, UserRole
from app.models.user import UserModel


class UsersRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._collection = db["users"]

    async def ensure_indexes(self) -> None:
        await self._collection.create_index("email_normalized", unique=True)
        await self._collection.create_index("nickname", unique=True)
        await self._collection.create_index("nickname_normalized", unique=True)

    async def create(
        self,
        *,
        email: str,
        password_hash: str,
        role: UserRole,
        nickname: str,
        first_name: str | None = None,
        last_name: str | None = None,
        must_change_password: bool = False,
    ) -> UserModel:
        now = datetime.now(UTC)
        email_normalized = email.strip().lower()
        nickname_normalized = nickname.strip().lower()
        doc = {
            "email_normalized": email_normalized,
            "password_hash": password_hash,
            "password_updated_at": now,
            "role": role.value,
            "account_status": UserAccountStatus.ACTIVE.value,
            "email_verified_at": None,
            "nickname": nickname,
            "nickname_normalized": nickname_normalized,
            "first_name": first_name,
            "last_name": last_name,
            "organization": None,
            "biography": None,
            "avatar": None,
            "must_change_password": must_change_password,
            "last_login_at": None,
            "created_at": now,
            "updated_at": now,
        }
        result = await self._collection.insert_one(doc)
        doc["_id"] = str(result.inserted_id)
        return UserModel.model_validate(doc)

    async def create_bootstrap_account(
        self,
        *,
        email: str,
        password_hash: str,
        nickname: str,
        role: UserRole,
    ) -> UserModel:
        """Bootstrap dev/local user: verified, active, no mandatory password change."""
        now = datetime.now(UTC)
        email_normalized = email.strip().lower()
        nickname_normalized = nickname.strip().lower()
        doc = {
            "email_normalized": email_normalized,
            "password_hash": password_hash,
            "password_updated_at": now,
            "role": role.value,
            "account_status": UserAccountStatus.ACTIVE.value,
            "email_verified_at": now,
            "nickname": nickname.strip(),
            "nickname_normalized": nickname_normalized,
            "first_name": None,
            "last_name": None,
            "organization": None,
            "biography": None,
            "avatar": None,
            "must_change_password": False,
            "last_login_at": None,
            "created_at": now,
            "updated_at": now,
        }
        result = await self._collection.insert_one(doc)
        doc["_id"] = str(result.inserted_id)
        return UserModel.model_validate(doc)

    async def create_admin_account(
        self,
        *,
        email: str,
        password_hash: str,
        nickname: str,
    ) -> UserModel:
        """Bootstrap first admin (verified, active, no mandatory password change)."""
        return await self.create_bootstrap_account(
            email=email,
            password_hash=password_hash,
            nickname=nickname,
            role=UserRole.ADMIN,
        )

    async def get_by_email(self, email: str) -> UserModel | None:
        normalized = email.strip().lower()
        doc = await self._collection.find_one({"email_normalized": normalized})
        return self._to_model(doc)

    async def get_by_nickname(self, nickname: str) -> UserModel | None:
        normalized = nickname.strip().lower()
        doc = await self._collection.find_one({"nickname_normalized": normalized})
        return self._to_model(doc)

    async def list_ids_matching_nickname(self, q: str) -> list[str]:
        """User ids whose nickname matches the search text (case-insensitive substring)."""
        trimmed = q.strip()
        if not trimmed:
            return []
        pattern = re.escape(trimmed)
        query = {
            "$or": [
                {"nickname": {"$regex": pattern, "$options": "i"}},
                {"nickname_normalized": {"$regex": pattern, "$options": "i"}},
            ]
        }
        ids: list[str] = []
        cursor = self._collection.find(query)
        async for doc in cursor:
            oid = doc.get("_id")
            if oid is not None:
                ids.append(str(oid))
        return ids

    async def list_by_roles(self, roles: list[UserRole]) -> list[UserModel]:
        if not roles:
            return []
        role_values = [r.value for r in roles]
        cursor = self._collection.find({"role": {"$in": role_values}}).sort("nickname_normalized", 1)
        out: list[UserModel] = []
        async for doc in cursor:
            model = self._to_model(doc)
            if model is not None:
                out.append(model)
        return out

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
        return await self.list_verified_emails_by_roles([role])

    async def list_verified_emails_by_roles(self, roles: list[str]) -> list[str]:
        if not roles:
            return []
        cursor = self._collection.find(
            {
                "role": {"$in": roles},
                "email_verified_at": {"$ne": None},
                "account_status": UserAccountStatus.ACTIVE.value,
            },
            {"email_normalized": 1, "_id": 0},
        )
        out: list[str] = []
        async for doc in cursor:
            addr = doc.get("email_normalized")
            if isinstance(addr, str) and addr:
                out.append(addr)
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
            {"$set": {"email_verified_at": datetime.now(UTC), "updated_at": datetime.now(UTC)}},
        )
        return result.modified_count == 1

    async def apply_profile_updates(self, user_id: str, updates: dict[str, Any]) -> UserModel | None:
        if not ObjectId.is_valid(user_id) or not updates:
            return None
        updates = {**updates, "updated_at": datetime.now(UTC)}
        result = await self._collection.update_one({"_id": ObjectId(user_id)}, {"$set": updates})
        if result.matched_count == 0:
            return None
        doc = await self._collection.find_one({"_id": ObjectId(user_id)})
        return self._to_model(doc)

    async def set_avatar(self, user_id: str, *, avatar: dict[str, Any] | None) -> UserModel | None:
        if not ObjectId.is_valid(user_id):
            return None
        now = datetime.now(UTC)
        result = await self._collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"avatar": avatar, "updated_at": now}},
        )
        if result.matched_count == 0:
            return None
        doc = await self._collection.find_one({"_id": ObjectId(user_id)})
        return self._to_model(doc)

    async def set_password_hash(self, user_id: str, *, password_hash: str) -> UserModel | None:
        if not ObjectId.is_valid(user_id):
            return None
        now = datetime.now(UTC)
        result = await self._collection.update_one(
            {"_id": ObjectId(user_id)},
            {
                "$set": {
                    "password_hash": password_hash,
                    "password_updated_at": now,
                    "must_change_password": False,
                    "updated_at": now,
                }
            },
        )
        if result.matched_count == 0:
            return None
        doc = await self._collection.find_one({"_id": ObjectId(user_id)})
        return self._to_model(doc)

    async def set_role(self, user_id: str, *, role: UserRole) -> UserModel | None:
        if not ObjectId.is_valid(user_id):
            return None
        now = datetime.now(UTC)
        result = await self._collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"role": role.value, "updated_at": now}},
        )
        if result.matched_count == 0:
            return None
        doc = await self._collection.find_one({"_id": ObjectId(user_id)})
        return self._to_model(doc)

    async def set_account_status(self, user_id: str, *, account_status: UserAccountStatus) -> UserModel | None:
        if not ObjectId.is_valid(user_id):
            return None
        now = datetime.now(UTC)
        result = await self._collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"account_status": account_status.value, "updated_at": now}},
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
