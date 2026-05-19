"""Remove legacy Spanish slug rows from scenario_classification_catalog before re-seeding English entries."""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

LEGACY_SLUGS = (
    "aprendizaje-y-creatividad",
    "salud",
    "entretenimiento-y-ocio",
    "vida-diaria",
    "psicologia-y-bienestar",
    "personas-y-relaciones-sociales",
    "toma-de-decisiones",
    "supervision",
    "investigacion-cientifica-sobre-los-ninos",
)


def _mongodb_uri() -> str:
    env_file = REPO / ".env"
    default = "mongodb://localhost:27017/luneta"
    if not env_file.is_file():
        return os.environ.get("MONGODB_URI", default)
    for line in env_file.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("MONGODB_URI="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return os.environ.get("MONGODB_URI", default)


async def _run() -> int:
    from motor.motor_asyncio import AsyncIOMotorClient

    client = AsyncIOMotorClient(_mongodb_uri())
    coll = client.get_default_database()["scenario_classification_catalog"]
    result = await coll.delete_many({"slug": {"$in": list(LEGACY_SLUGS)}})
    print(f"Deleted {result.deleted_count} legacy classification row(s).")
    client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_run()))
