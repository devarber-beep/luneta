"""Verify MongoDB connectivity using MONGODB_URI from repo .env or environment.

Usage (venv active, from repo root):

    python infra/scripts/check_mongodb_connection.py
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

REPO = Path(__file__).resolve().parents[2]
if str(REPO / "apps" / "api") not in sys.path:
    sys.path.insert(0, str(REPO / "apps" / "api"))


def _mongodb_uri() -> str:
    env_file = REPO / ".env"
    default = "mongodb://localhost:27017/luneta"
    if not env_file.is_file():
        return os.environ.get("MONGODB_URI", default)
    for line in env_file.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("MONGODB_URI="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return os.environ.get("MONGODB_URI", default)


def _describe_uri(uri: str) -> str:
    parsed = urlparse(uri)
    scheme = parsed.scheme or "unknown"
    host = parsed.hostname or parsed.netloc or "?"
    db = (parsed.path or "").lstrip("/") or "(no database in path — use /luneta)"
    return f"scheme={scheme}, host={host}, database={db}"


async def _run() -> int:
    uri = _mongodb_uri()
    if any(token in uri for token in ("<db_password>", "YOUR_PASSWORD", "PASSWORD@", "USER:")):
        print("MONGODB_URI still contains placeholders. Edit .env with your Atlas password.")
        print(f"Expected format: {_describe_uri('mongodb+srv://user:pass@cluster.mongodb.net/luneta?retryWrites=true&w=majority')}")
        return 1

    print(f"Checking {_describe_uri(uri)} ...")

    from motor.motor_asyncio import AsyncIOMotorClient

    client = AsyncIOMotorClient(uri, serverSelectionTimeoutMS=10000)
    try:
        await client.admin.command("ping")
        db = client.get_default_database()
        db_name = db.name
        collections = await db.list_collection_names()
        print(f"OK — connected to database '{db_name}' ({len(collections)} collection(s)).")
        return 0
    except Exception as exc:
        print(f"FAILED — {exc}")
        print()
        print("Common fixes:")
        print("  1. Atlas -> Network Access -> add your IP (or 0.0.0.0/0 for cloud hosts).")
        print("  2. URI must include database name: ...mongodb.net/luneta?...")
        print("  3. URL-encode special characters in the password (@ -> %40, etc.).")
        return 1
    finally:
        client.close()


def main() -> None:
    raise SystemExit(asyncio.run(_run()))


if __name__ == "__main__":
    main()
