"""Backfill review_events.actor_role from users.role (idempotent).

Run after Milestone 3 when historical events lack actor_role. Safe to re-run.
"""
from __future__ import annotations

import os
from pathlib import Path

from bson import ObjectId
from pymongo import MongoClient

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

    missing_filter = {"$or": [{"actor_role": {"$exists": False}}, {"actor_role": None}]}
    total_missing = events.count_documents(missing_filter)
    if total_missing == 0:
        print({"message": "No review_events need actor_role backfill", "uri_tail": uri.split("@")[-1]})
        return 0

    updated = 0
    skipped_no_user = 0
    orphan_doc_ids: list[str] = []
    for doc in events.find(missing_filter):
        uid = doc.get("actor_user_id")
        if not uid or not isinstance(uid, str):
            skipped_no_user += 1
            orphan_doc_ids.append(str(doc["_id"]))
            continue
        if not ObjectId.is_valid(uid):
            skipped_no_user += 1
            orphan_doc_ids.append(str(doc["_id"]))
            continue
        user = users.find_one({"_id": ObjectId(uid)}, {"role": 1})
        if not user or not user.get("role"):
            skipped_no_user += 1
            orphan_doc_ids.append(str(doc["_id"]))
            continue
        role_raw = user["role"]
        legacy = {"author": "investigator", "reviewer": "coordinator"}
        actor_role = legacy.get(role_raw, role_raw)
        if actor_role not in ("investigator", "coordinator"):
            skipped_no_user += 1
            orphan_doc_ids.append(str(doc["_id"]))
            continue
        result = events.update_one({"_id": doc["_id"]}, {"$set": {"actor_role": actor_role}})
        if result.modified_count:
            updated += 1

    remaining = events.count_documents(missing_filter)
    out = {
        "database": db.name,
        "review_events_missing_before": total_missing,
        "backfilled_actor_role": updated,
        "skipped_missing_or_unknown_user": skipped_no_user,
        "review_events_still_missing_actor_role": remaining,
    }
    if orphan_doc_ids:
        out["orphan_event_ids_sample"] = orphan_doc_ids[:20]
    print(out)
    if remaining:
        print(
            "NOTE: Some events still lack actor_role (deleted/invalid actor_user_id). "
            "The API model allows null; fix manually or delete orphan audit rows if desired."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
