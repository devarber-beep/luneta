"""Report collaborator role values stored in MongoDB (read-only)."""
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
        print(f"Cannot connect to MongoDB at {uri!r}: {exc}", file=sys.stderr)
        sys.exit(1)

    db = client.get_default_database()
    print(f"database: {db.name}")

    for role_value in ("owner", "editor", "collaborator"):
        count = await db.scenarios.count_documents({"collaborators.role": role_value})
        print(f"scenarios with collaborators.role={role_value!r}: {count}")

    legacy = await db.scenarios.find(
        {"collaborators.role": "editor"},
        {"title": 1, "collaborators": 1},
    ).to_list(length=5)
    if legacy:
        print("\nSample scenarios still using role 'editor':")
        for doc in legacy:
            print(f"  - {doc.get('_id')}: {doc.get('title')!r}")

    total = await db.scenarios.count_documents({})
    print(f"\ntotal scenarios: {total}")
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
