"""Migrate persisted role strings: author→investigator, reviewer→coordinator.

Run once before or immediately after deploying API code that expects the new enum.
Idempotent: safe to re-run.
"""
from __future__ import annotations

import os
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
    db = MongoClient(uri).get_default_database()
    users = db["users"]
    events = db["review_events"]

    u_author = users.update_many({"role": "author"}, {"$set": {"role": "investigator"}})
    u_rev = users.update_many({"role": "reviewer"}, {"$set": {"role": "coordinator"}})
    e_author = events.update_many({"actor_role": "author"}, {"$set": {"actor_role": "investigator"}})
    e_rev = events.update_many({"actor_role": "reviewer"}, {"$set": {"actor_role": "coordinator"}})

    print(
        {
            "database": db.name,
            "users_matched_author": u_author.matched_count,
            "users_modified_author": u_author.modified_count,
            "users_matched_reviewer": u_rev.matched_count,
            "users_modified_reviewer": u_rev.modified_count,
            "review_events_matched_author": e_author.matched_count,
            "review_events_modified_author": e_author.modified_count,
            "review_events_matched_reviewer": e_rev.matched_count,
            "review_events_modified_reviewer": e_rev.modified_count,
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
