"""Shared test fixtures with in-memory DB override."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest
from bson import ObjectId
from httpx import ASGITransport, AsyncClient

from app.db import get_db
from app.main import app


@dataclass
class _InsertOneResult:
    inserted_id: ObjectId


@dataclass
class _UpdateResult:
    modified_count: int
    matched_count: int = 1


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

    def sort(self, key: str, direction: int) -> "FakeCursor":
        reverse = direction == -1
        self._docs = sorted(self._docs, key=lambda doc: doc.get(key), reverse=reverse)
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

    def find(self, query: dict[str, Any], projection: dict[str, Any] | None = None) -> FakeCursor:
        matched = [dict(doc) for doc in self._docs if _matches(doc, query)]
        if projection:
            keys = {k for k, v in projection.items() if v and k != "_id"}
            if projection.get("_id") == 0:
                matched = [{k: doc[k] for k in keys if k in doc} for doc in matched]
            else:
                matched = [{k: doc.get(k) for k in keys if k in doc} for doc in matched]
        return FakeCursor(matched)


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
        value = doc.get(key)
        if isinstance(expected, dict):
            if "$in" in expected:
                allowed = expected["$in"]
                if value not in allowed:
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
                exists = key in doc
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
def fake_db() -> FakeDB:
    return FakeDB()


@pytest.fixture
async def api_client(fake_db: FakeDB):
    async def _get_test_db():
        return fake_db

    app.dependency_overrides[get_db] = _get_test_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()
