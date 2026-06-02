"""Seed ethical risk catalog entries (English labels).

Usage (venv active, from repo root):

    python infra/scripts/seed_ethical_risk_catalog.py
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO / "apps" / "api") not in sys.path:
    sys.path.insert(0, str(REPO / "apps" / "api"))

ETHICAL_RISKS: list[tuple[str, str]] = [
    ("privacy-violation", "Privacy violation"),
    ("behavioral-manipulation", "Behavioral manipulation"),
    ("emotional-or-physical-harm", "Emotional or physical harm"),
    ("inappropriate-content", "Inappropriate content"),
    ("excessive-dependence", "Excessive dependence"),
    ("lack-of-algorithmic-transparency", "Lack of algorithmic transparency"),
    ("accountability-gap", "Accountability gap"),
    ("addictive-behavior-design", "Addictive behavior design"),
    ("ai-control-over-child", "AI control over the child"),
    ("over-trust", "Over-trust"),
    ("misinformation-and-deceptive-content", "Misinformation and deceptive content"),
    ("failure-to-identify-as-ai-agent", "Failure to identify as an AI agent"),
]

DEPRECATED_SLUGS: list[str] = [
    "algorithmic-bias-and-discrimination",
    "intellectual-property-violation",
    "erosion-of-cognitive-skills",
    "erosion-of-social-skills",
    "simulation-of-humanity",
    "interested-emotional-bonding",
    "dehumanizing-design",
    "negligent-design",
    "ethical-principles-misalignment",
    "inequality-generation",
    "anthropomorphism",
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
    from datetime import UTC, datetime

    from motor.motor_asyncio import AsyncIOMotorClient

    from app.repositories.ethical_risks import EthicalRisksRepository

    client = AsyncIOMotorClient(_mongodb_uri())
    db = client.get_default_database()
    repo = EthicalRisksRepository(db)
    await repo.ensure_indexes()
    now = datetime.now(UTC)

    for order, (slug, label) in enumerate(ETHICAL_RISKS):
        entry = await repo.upsert_seed_entry(slug=slug, label=label, sort_order=order)
        await db["ethical_risk_catalog"].update_one(
            {"slug": slug},
            {"$set": {"is_active": True, "updated_at": now}},
        )
        print(f"  active {entry.slug} ({entry.id})")

    for slug in DEPRECATED_SLUGS:
        result = await db["ethical_risk_catalog"].update_many(
            {"slug": slug},
            {"$set": {"is_active": False, "updated_at": now}},
        )
        if result.modified_count:
            print(f"  deactivated {slug} ({result.modified_count})")

    print(f"Seeded {len(ETHICAL_RISKS)} active ethical risk entries.")
    client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_run()))
