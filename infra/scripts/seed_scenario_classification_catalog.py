"""Seed flat scenario category catalog (English labels).

Usage (venv active, from repo root):

    python infra/scripts/seed_scenario_classification_catalog.py

Idempotent: upserts by slug.
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO / "apps" / "api") not in sys.path:
    sys.path.insert(0, str(REPO / "apps" / "api"))

TOP_LEVEL_CATEGORIES: list[tuple[str, str]] = [
    ("learning-and-creativity", "Learning and creativity"),
    ("health", "Health"),
    ("entertainment-and-leisure", "Entertainment and leisure"),
    ("daily-life", "Daily life"),
    ("psychology-and-wellbeing", "Psychology and wellbeing"),
    ("people-and-social-relationships", "People and social relationships"),
    ("decision-making", "Decision making"),
    ("supervision", "Supervision"),
    ("scientific-research-on-children", "Scientific research on children"),
]


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

    from app.repositories.scenario_classification import ScenarioClassificationRepository

    client = AsyncIOMotorClient(_mongodb_uri())
    db = client.get_default_database()
    repo = ScenarioClassificationRepository(db)
    await repo.ensure_indexes()

    for order, (slug, label) in enumerate(TOP_LEVEL_CATEGORIES):
        entry = await repo.upsert_seed_entry(slug=slug, label=label, sort_order=order)
        print(f"  {entry.slug} ({entry.id})")

    print(f"Seeded {len(TOP_LEVEL_CATEGORIES)} top-level categories.")
    client.close()
    return 0


def main() -> int:
    return asyncio.run(_run())


if __name__ == "__main__":
    raise SystemExit(main())
