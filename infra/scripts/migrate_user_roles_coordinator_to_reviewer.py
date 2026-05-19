"""One-time data fix: role slug ``coordinator`` -> ``reviewer`` (idempotent).

Updates:
  - ``users.role``
  - ``review_events.actor_role``

A second run typically matches zero documents.
"""
from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path

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
    now = datetime.now(UTC)

    users_res = db["users"].update_many(
        {"role": "coordinator"},
        {"$set": {"role": "reviewer", "updated_at": now}},
    )
    events_res = db["review_events"].update_many(
        {"actor_role": "coordinator"},
        {"$set": {"actor_role": "reviewer"}},
    )
    out = {
        "database": db.name,
        "users_matched": users_res.matched_count,
        "users_modified": users_res.modified_count,
        "review_events_matched": events_res.matched_count,
        "review_events_modified": events_res.modified_count,
    }
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
