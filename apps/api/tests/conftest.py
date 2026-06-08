"""Shared test fixtures with in-memory DB override.

Set LUNETA_TEST_REAL_DB=1 to run HTTP tests against MongoDB from MONGODB_URI (e.g. Docker).
A session-start hook removes rows tied to fixed test emails so runs stay repeatable.
Run pytest from ``apps/api`` so ``.env`` loads if present.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import pytest
from bson import ObjectId
from httpx import ASGITransport, AsyncClient

from app.core.security import hash_password
from app.db import get_db
from app.deps.storage import get_user_avatar_storage
from app.main import app
from app.models.user import UserAvatarModel


def user_doc(
    *,
    email: str,
    role: str,
    password_plain: str = "UserPass123!",
    account_status: str = "active",
    verified: bool = True,
    first_name: str | None = None,
    last_name: str | None = None,
) -> dict:
    """Build a user document for in-memory or integration HTTP tests."""
    now = datetime.now(UTC)
    normalized = email.strip().lower()
    local = normalized.split("@")[0][:10] or "user"
    fn = first_name or local.capitalize()
    ln = last_name or "User"
    display = f"{fn} {ln}"
    return {
        "email_normalized": normalized,
        "password_hash": hash_password(password_plain),
        "password_updated_at": now,
        "role": role,
        "account_status": account_status,
        "email_verified_at": now if verified else None,
        "first_name": fn,
        "last_name": ln,
        "display_name": display,
        "display_name_normalized": display.lower(),
        "university": None,
        "university_normalized": None,
        "biography": None,
        "avatar": None,
        "must_change_password": False,
        "last_login_at": None,
        "created_at": now,
        "updated_at": now,
    }


def signup_body(
    *,
    email: str,
    password: str = "Password123!",
    first_name: str | None = None,
    last_name: str | None = None,
) -> dict[str, str]:
    """JSON body for POST /auth/signup in HTTP tests."""
    local = email.strip().lower().split("@")[0]
    fn = first_name or local.capitalize()
    ln = last_name or "User"
    return {"email": email, "password": password, "first_name": fn, "last_name": ln}


def use_real_mongo() -> bool:
    return os.environ.get("LUNETA_TEST_REAL_DB", "").strip().lower() in ("1", "true", "yes")


class _FakeUserAvatarStorage:
    bucket: str = "test-bucket"

    def ensure_bucket(self) -> None:
        return None

    def upload_avatar(self, *, user_id: str, content: bytes, content_type: str) -> UserAvatarModel:
        return UserAvatarModel(
            bucket=self.bucket,
            object_key=f"users/{user_id}/avatar/fake-id",
            version_id=None,
            content_type=content_type,
            size_bytes=len(content),
            updated_at=datetime.now(UTC),
        )

    def delete_object(self, *, object_key: str) -> None:
        return None

    def presigned_get_url(self, *, object_key: str, expires_seconds: int = 900) -> str:
        return f"http://test-presigned/{object_key}"


# Emails used by integration tests; purged from Mongo when LUNETA_TEST_REAL_DB=1.
_INTEGRATION_TEST_EMAILS: tuple[str, ...] = (
    "author@luneta.dev",
    "reviewer@luneta.dev",
    "selfrev@luneta.dev",
    "regonly@luneta.dev",
    "snap@luneta.dev",
    "mcplogin@luneta.dev",
    "mcpgate@luneta.dev",
    "mcpprof@luneta.dev",
    "mcpavatar@luneta.dev",
    "mcpdis@luneta.dev",
    "admrf1@luneta.dev",
    "invcreate@luneta.dev",
    "regprom@luneta.dev",
    "revonly@luneta.dev",
    "invcreate2@luneta.dev",
    "invrev@luneta.dev",
    "todeact@luneta.dev",
    "auditinv@luneta.dev",
    "phase1admin@luneta.dev",
    "disabledinv@luneta.dev",
    "phase1rev@luneta.dev",
    "phase1inv@luneta.dev",
    "catalogadmin@luneta.dev",
)


def pytest_sessionstart(session: pytest.Session) -> None:
    if not use_real_mongo():
        return
    from app.db import reset_client

    reset_client()
    from pymongo import MongoClient

    from app.settings import settings

    client = MongoClient(settings.mongodb_uri)
    db = client.get_default_database()
    normalized = [e.strip().lower() for e in _INTEGRATION_TEST_EMAILS]
    users = list(db.users.find({"email_normalized": {"$in": normalized}}, {"_id": 1}))
    user_id_strs = [str(u["_id"]) for u in users]
    if user_id_strs:
        scenarios = list(db.scenarios.find({"author_user_id": {"$in": user_id_strs}}, {"_id": 1}))
        scenario_id_strs = [str(s["_id"]) for s in scenarios]
        if scenario_id_strs:
            db.review_events.delete_many({"scenario_id": {"$in": scenario_id_strs}})
            db.scenario_revisions.delete_many({"scenario_id": {"$in": scenario_id_strs}})
            db.suggestions.delete_many({"scenario_id": {"$in": scenario_id_strs}})
            db.scenario_evaluations.delete_many({"scenario_id": {"$in": scenario_id_strs}})
        db.scenarios.delete_many({"author_user_id": {"$in": user_id_strs}})
    db.users.delete_many({"email_normalized": {"$in": normalized}})
    for email in _INTEGRATION_TEST_EMAILS:
        db.email_verification_tokens.delete_many({"email": email})
    client.close()


@pytest.fixture(autouse=True)
def _motor_singleton_per_test():
    yield
    if use_real_mongo():
        from app.db import reset_client

        reset_client()


@dataclass
class _InsertOneResult:
    inserted_id: ObjectId


@dataclass
class _UpdateResult:
    modified_count: int
    matched_count: int = 1


@dataclass
class _DeleteResult:
    deleted_count: int


def _apply_update_pipeline(doc: dict[str, Any], pipeline: list[dict[str, Any]]) -> dict[str, Any]:
    out = dict(doc)
    for stage in pipeline:
        if "$set" not in stage:
            continue
        for k, v in stage["$set"].items():
            if isinstance(v, str) and v.startswith("$") and not v.startswith("$$"):
                src = v[1:]
                out[k] = out.get(src)
            else:
                out[k] = v
    return out


class FakeCursor:
    def __init__(self, docs: list[dict[str, Any]]) -> None:
        self._docs = docs
        self._idx = 0

    def sort(self, key: str | list[tuple[str, int]], direction: int | None = None) -> "FakeCursor":
        if isinstance(key, list):
            for field, dir_int in reversed(key):
                reverse = dir_int == -1
                self._docs = sorted(self._docs, key=lambda doc, f=field: doc.get(f), reverse=reverse)
        else:
            reverse = (direction or 1) == -1
            self._docs = sorted(self._docs, key=lambda doc, f=key: doc.get(f), reverse=reverse)
        return self

    def skip(self, count: int) -> "FakeCursor":
        self._docs = self._docs[count:]
        return self

    def limit(self, count: int) -> "FakeCursor":
        self._docs = self._docs[:count]
        return self

    def __aiter__(self) -> "FakeCursor":
        self._idx = 0
        return self

    async def __anext__(self) -> dict[str, Any]:
        if self._idx >= len(self._docs):
            raise StopAsyncIteration
        item = self._docs[self._idx]
        self._idx += 1
        return item


class FakeAggregateCursor:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows
        self._idx = 0

    def __aiter__(self) -> "FakeAggregateCursor":
        self._idx = 0
        return self

    async def __anext__(self) -> dict[str, Any]:
        if self._idx >= len(self._rows):
            raise StopAsyncIteration
        item = self._rows[self._idx]
        self._idx += 1
        return item


class FakeCollection:
    def __init__(self) -> None:
        self._docs: list[dict[str, Any]] = []

    async def create_index(self, *_args, **_kwargs) -> None:
        return None

    async def insert_one(self, doc: dict[str, Any]) -> _InsertOneResult:
        stored = dict(doc)
        if "_id" not in stored:
            stored["_id"] = ObjectId()
        self._docs.append(stored)
        return _InsertOneResult(inserted_id=stored["_id"])

    async def find_one(self, query: dict[str, Any]) -> dict[str, Any] | None:
        for doc in self._docs:
            if _matches(doc, query):
                return dict(doc)
        return None

    async def update_one(
        self, query: dict[str, Any], update: dict[str, Any] | list[dict[str, Any]]
    ) -> _UpdateResult:
        for idx, doc in enumerate(self._docs):
            if not _matches(doc, query):
                continue
            if isinstance(update, list):
                self._docs[idx] = _apply_update_pipeline(doc, update)
            else:
                updated = dict(doc)
                for key, value in update.get("$set", {}).items():
                    updated[key] = value
                for key, value in update.get("$inc", {}).items():
                    updated[key] = updated.get(key, 0) + value
                self._docs[idx] = updated
            return _UpdateResult(modified_count=1, matched_count=1)
        return _UpdateResult(modified_count=0, matched_count=0)

    async def delete_one(self, query: dict[str, Any]) -> _DeleteResult:
        for idx, doc in enumerate(self._docs):
            if _matches(doc, query):
                del self._docs[idx]
                return _DeleteResult(deleted_count=1)
        return _DeleteResult(deleted_count=0)

    async def update_many(
        self, query: dict[str, Any], update: dict[str, Any] | list[dict[str, Any]]
    ) -> _UpdateResult:
        modified = 0
        for idx, doc in enumerate(self._docs):
            if not _matches(doc, query):
                continue
            if isinstance(update, list):
                self._docs[idx] = _apply_update_pipeline(doc, update)
            else:
                updated = dict(doc)
                for key, value in update.get("$set", {}).items():
                    updated[key] = value
                for key, value in update.get("$inc", {}).items():
                    updated[key] = updated.get(key, 0) + value
                self._docs[idx] = updated
            modified += 1
        return _UpdateResult(modified_count=modified, matched_count=modified)

    async def count_documents(self, query: dict[str, Any]) -> int:
        return sum(1 for doc in self._docs if _matches(doc, query))

    def find(self, query: dict[str, Any], projection: dict[str, Any] | None = None) -> FakeCursor:
        matched = [dict(doc) for doc in self._docs if _matches(doc, query)]
        if projection:
            keys = {k for k, v in projection.items() if v and k != "_id"}
            if projection.get("_id") == 0:
                matched = [{k: doc[k] for k in keys if k in doc} for doc in matched]
            else:
                matched = [{k: doc.get(k) for k in keys if k in doc} for doc in matched]
        return FakeCursor(matched)

    def aggregate(self, pipeline: list[dict[str, Any]]) -> FakeAggregateCursor:
        docs = list(self._docs)
        rows: list[dict[str, Any]] = []
        for stage in pipeline:
            if "$match" in stage:
                docs = [doc for doc in docs if _matches(doc, stage["$match"])]
                continue
            if "$group" in stage:
                group = stage["$group"]
                group_id = group.get("_id")
                if isinstance(group_id, str) and group_id.startswith("$"):
                    field = group_id[1:]
                    buckets: dict[Any, dict[str, Any]] = {}
                    for doc in docs:
                        key = doc.get(field)
                        if key not in buckets:
                            buckets[key] = {"_id": key}
                        for out_key, spec in group.items():
                            if out_key == "_id" or not isinstance(spec, dict):
                                continue
                            if "$sum" in spec:
                                buckets[key][out_key] = buckets[key].get(out_key, 0) + 1
                                continue
                            if "$first" in spec:
                                src = spec["$first"]
                                if isinstance(src, str) and src.startswith("$") and out_key not in buckets[key]:
                                    buckets[key][out_key] = doc.get(src[1:])
                    rows = list(buckets.values())
                continue
            if "$sort" in stage:
                sort_spec = stage["$sort"]
                target = rows if rows else docs
                for field, direction in reversed(list(sort_spec.items())):
                    reverse = direction == -1
                    target.sort(key=lambda row, f=field: row.get(f), reverse=reverse)
                if rows:
                    rows = target
                else:
                    docs = target
        return FakeAggregateCursor(rows if rows else docs)


def _doc_value(doc: dict[str, Any], key: str) -> Any:
    if "." not in key:
        return doc.get(key)
    current: Any = doc
    for part in key.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def _path_exists(doc: dict[str, Any], key: str) -> bool:
    if "." not in key:
        return key in doc
    current: Any = doc
    for part in key.split("."):
        if not isinstance(current, dict) or part not in current:
            return False
        current = current[part]
    return True


def _matches(doc: dict[str, Any], query: dict[str, Any]) -> bool:
    if "$or" in query:
        branches = query["$or"]
        if not isinstance(branches, list) or not any(_matches(doc, sub) for sub in branches):
            return False
        rest = {k: v for k, v in query.items() if k != "$or"}
        return _matches(doc, rest) if rest else True
    if "$and" in query:
        parts = query["$and"]
        if not isinstance(parts, list) or not all(_matches(doc, p) for p in parts):
            return False
        rest = {k: v for k, v in query.items() if k != "$and"}
        return _matches(doc, rest) if rest else True
    for key, expected in query.items():
        value = _doc_value(doc, key)
        if isinstance(expected, dict):
            if "$in" in expected:
                allowed = expected["$in"]
                if isinstance(value, list):
                    if not any(item in allowed for item in value):
                        return False
                elif value not in allowed:
                    return False
                continue
            if "$regex" in expected:
                if not isinstance(value, str):
                    return False
                flags = re.I if "i" in str(expected.get("$options", "")) else 0
                if re.search(str(expected["$regex"]), value, flags) is None:
                    return False
                continue
            if "$gte" in expected:
                threshold = expected["$gte"]
                if value is None or value < threshold:
                    return False
                continue
            if "$lte" in expected:
                threshold = expected["$lte"]
                if value is None or value > threshold:
                    return False
                continue
            if "$ne" in expected and value == expected["$ne"]:
                return False
            if "$ne" in expected:
                continue
            if "$type" in expected:
                want = expected["$type"]
                if want == "string" and not isinstance(value, str):
                    return False
                continue
            if "$exists" in expected:
                exists = _path_exists(doc, key)
                if expected["$exists"] and not exists:
                    return False
                if not expected["$exists"] and exists:
                    return False
                continue
            if "$gt" in expected:
                threshold = expected["$gt"]
                if threshold is None:
                    # Match real Mongo: $gt null does not select dates; tests follow repository ($ne: null).
                    return False
                elif not (value is not None and value > threshold):
                    return False
            continue
        if key == "collaborators.user_id":
            collabs = doc.get("collaborators") or []
            if not any(c.get("user_id") == expected for c in collabs):
                return False
            continue
        if value != expected:
            return False
    return True


class FakeDB:
    def __init__(self) -> None:
        self._collections: dict[str, FakeCollection] = {}

    def __getitem__(self, collection_name: str) -> FakeCollection:
        if collection_name not in self._collections:
            self._collections[collection_name] = FakeCollection()
        return self._collections[collection_name]


@pytest.fixture
async def fake_db():
    if use_real_mongo():
        db = await get_db()
        yield db
    else:
        yield FakeDB()


@pytest.fixture
async def api_client(fake_db):
    if use_real_mongo():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield client
    else:
        async def _get_test_db():
            return fake_db

        app.dependency_overrides[get_db] = _get_test_db
        app.dependency_overrides[get_user_avatar_storage] = lambda: _FakeUserAvatarStorage()
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                yield client
        finally:
            app.dependency_overrides.clear()
