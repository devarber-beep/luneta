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

    async def update_one(self, query: dict[str, Any], update: dict[str, Any]) -> _UpdateResult:
        for idx, doc in enumerate(self._docs):
            if not _matches(doc, query):
                continue
            updated = dict(doc)
            for key, value in update.get("$set", {}).items():
                updated[key] = value
            for key, value in update.get("$inc", {}).items():
                updated[key] = updated.get(key, 0) + value
            self._docs[idx] = updated
            return _UpdateResult(modified_count=1)
        return _UpdateResult(modified_count=0)

    def find(self, query: dict[str, Any]) -> FakeCursor:
        return FakeCursor([dict(doc) for doc in self._docs if _matches(doc, query)])


def _matches(doc: dict[str, Any], query: dict[str, Any]) -> bool:
    if "$or" in query:
        branches = query["$or"]
        if not isinstance(branches, list) or not any(_matches(doc, sub) for sub in branches):
            return False
        rest = {k: v for k, v in query.items() if k != "$or"}
        return _matches(doc, rest) if rest else True
    for key, expected in query.items():
        value = doc.get(key)
        if isinstance(expected, dict):
            if "$gt" in expected and not (value is not None and value > expected["$gt"]):
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
