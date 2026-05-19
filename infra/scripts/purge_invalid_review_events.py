"""Remove review_events rows that violate the current contract.

Deletes documents that:
  - lack ``actor_role``, or
  - have an ``actor_user_id`` that is not a valid ObjectId, or
  - reference no existing user in ``users``.

Run once (or whenever) after tightening validation; not a compatibility layer.
"""
from __future__ import annotations

import os
from pathlib import Path

from bson import ObjectId
from pymongo import MongoClient

ALLOWED_ACTOR_ROLES = frozenset({"registered", "investigator", "reviewer", "admin"})

REPO = Path(__file__).resolve().parents[2]


def _mongodb_uri() -> str:
    env_file = REPO / ".env"
    default = "mongodb://localhost:27017/luneta"
    if not env_file.is_file():
        return os.environ.get("MONGODB_URI", default)
    for line in env_file.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("MONGODB_URI="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return os.environ.get("MONGODB_URI", default)


def main() -> int:
    uri = _mongodb_uri()
    client = MongoClient(uri)
    db = client.get_default_database()
    events = db["review_events"]
    users = db["users"]

    to_delete: list[ObjectId] = []
    for doc in events.find({}):
        oid = doc.get("_id")
        if not isinstance(oid, ObjectId):
            continue
        role = doc.get("actor_role")
        if role not in ALLOWED_ACTOR_ROLES:
            to_delete.append(oid)
            continue
        uid = doc.get("actor_user_id")
        if not uid or not isinstance(uid, str) or not ObjectId.is_valid(uid):
            to_delete.append(oid)
            continue
        if users.count_documents({"_id": ObjectId(uid)}, limit=1) == 0:
            to_delete.append(oid)

    scanned = events.count_documents({})
    deleted = 0
    if to_delete:
        res = events.delete_many({"_id": {"$in": to_delete}})
        deleted = res.deleted_count

    print({"database": db.name, "scanned": scanned, "invalid_review_events_deleted": deleted})
    client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
