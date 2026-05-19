"""
Align Mongo with the current scenario and category catalog contract.

- Scenarios: category_ids only; drop body_markdown, category_id, subcategory_id;
  public_description (from public_body_markdown or description).
- Catalog: flat categories only; drop parent_id.
- Revisions: description only; drop body_markdown.

Run only after backup. From repo root with venv active:
  python infra/scripts/migrate_scenario_category_ids_flat.py
"""
from __future__ import annotations

import os
import sys

from bson import ObjectId
from pymongo import MongoClient

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
API_ROOT = os.path.join(ROOT, "apps", "api")
if API_ROOT not in sys.path:
    sys.path.insert(0, API_ROOT)

from app.settings import settings  # noqa: E402


def main() -> None:
    client = MongoClient(settings.mongodb_uri)
    db = client.get_default_database()

    catalog = db["scenario_classification_catalog"]
    removed_parent = catalog.update_many({}, {"$unset": {"parent_id": ""}})
    print(f"Catalog entries cleared of parent_id: {removed_parent.modified_count}")

    revisions = db["scenario_revisions"]
    for doc in revisions.find({"body_markdown": {"$exists": True}}):
        desc = doc.get("description") or doc.get("body_markdown") or ""
        revisions.update_one(
            {"_id": doc["_id"]},
            {"$set": {"description": desc}, "$unset": {"body_markdown": ""}},
        )
    print("Scenario revisions migrated to description-only")

    scenarios = db["scenarios"]
    count = 0
    for doc in scenarios.find({}):
        ids: list[str] = list(doc.get("category_ids") or [])
        for legacy in ("category_id", "subcategory_id"):
            val = doc.get(legacy)
            if val:
                lid = str(val) if isinstance(val, ObjectId) else str(val)
                if lid not in ids:
                    ids.append(lid)
        unset: dict[str, str] = {
            "body_markdown": "",
            "category_id": "",
            "subcategory_id": "",
            "public_body_markdown": "",
        }
        public_desc = doc.get("public_description")
        if public_desc is None:
            public_desc = doc.get("public_body_markdown") or doc.get("description") or ""
        scenarios.update_one(
            {"_id": doc["_id"]},
            {
                "$set": {"category_ids": ids, "public_description": public_desc},
                "$unset": unset,
            },
        )
        count += 1
    print(f"Scenarios migrated: {count}")
    client.close()


if __name__ == "__main__":
    main()
