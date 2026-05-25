"""Migrate scenario.collaborators[].role from legacy 'editor' to 'collaborator'.

Run only after backup. Does not run automatically.
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

from motor.motor_asyncio import AsyncIOMotorClient


async def main() -> None:
    uri = os.environ.get("MONGODB_URI", "mongodb://localhost:27017/luneta")
    client = AsyncIOMotorClient(uri, serverSelectionTimeoutMS=5000)
    try:
        await client.admin.command("ping")
    except Exception as exc:
        print(f"Cannot connect: {exc}", file=sys.stderr)
        sys.exit(1)

    db = client.get_default_database()
    cursor = db.scenarios.find({"collaborators.role": "editor"}, {"title": 1, "collaborators": 1})
    targets = await cursor.to_list(length=100)
    if not targets:
        print("No documents with collaborators.role='editor'. Nothing to do.")
        client.close()
        return

    print(f"Found {len(targets)} scenario document(s) with legacy role 'editor':")
    for doc in targets:
        collabs = [
            c for c in doc.get("collaborators", []) if c.get("role") == "editor"
        ]
        print(f"  _id={doc['_id']} title={doc.get('title')!r}")
        for c in collabs:
            print(f"    collaborator user_id={c.get('user_id')} role=editor -> collaborator")

    if "--yes" not in sys.argv:
        print("\nRe-run with --yes to apply.")
        client.close()
        sys.exit(0)

    updated_ids: list[str] = []
    for doc in targets:
        sid = doc["_id"]
        new_collaborators = []
        changed = False
        for entry in doc.get("collaborators", []):
            row = dict(entry)
            if row.get("role") == "editor":
                row["role"] = "collaborator"
                changed = True
            new_collaborators.append(row)
        if changed:
            await db.scenarios.update_one(
                {"_id": sid},
                {"$set": {"collaborators": new_collaborators}},
            )
            updated_ids.append(str(sid))

    after = await db.scenarios.count_documents({"collaborators.role": "editor"})
    print(f"\nUpdated {len(updated_ids)} document(s): {', '.join(updated_ids)}")
    print(f"remaining scenarios with role 'editor': {after}")
    client.close()


if __name__ == "__main__":
    env_file = Path(__file__).resolve().parents[2] / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip().strip('"'))
    asyncio.run(main())
