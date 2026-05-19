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
    ("algorithmic-bias-and-discrimination", "Algorithmic bias and discrimination"),
    ("privacy-violation", "Privacy violation"),
    ("lack-of-algorithmic-transparency", "Lack of algorithmic transparency"),
    ("behavioral-manipulation", "Behavioral manipulation"),
    ("excessive-dependence", "Excessive dependence"),
    ("misinformation-and-deceptive-content", "Misinformation and deceptive content"),
    ("accountability-gap", "Accountability gap"),
    ("over-trust", "Over-trust"),
    ("anthropomorphism", "Anthropomorphism"),
    ("emotional-or-physical-harm", "Emotional or physical harm"),
    ("erosion-of-cognitive-skills", "Erosion of cognitive skills"),
    ("intellectual-property-violation", "Intellectual property violation"),
    ("erosion-of-social-skills", "Erosion of social skills"),
    ("inappropriate-content", "Inappropriate content"),
    ("failure-to-identify-as-ai-agent", "Failure to identify as an AI agent"),
    ("simulation-of-humanity", "Simulation of humanity"),
    ("interested-emotional-bonding", "Interested generation of emotional bonds"),
    ("dehumanizing-design", "Dehumanizing design"),
    ("addictive-behavior-design", "Addictive behavior design"),
    ("negligent-design", "Negligent design"),
    ("ethical-principles-misalignment", "Problems with the ethical principles used by the AI"),
    ("inequality-generation", "Generation of inequality"),
    ("ai-control-over-child", "AI control over the child"),
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

    from app.repositories.ethical_risks import EthicalRisksRepository

    client = AsyncIOMotorClient(_mongodb_uri())
    db = client.get_default_database()
    repo = EthicalRisksRepository(db)
    await repo.ensure_indexes()

    for order, (slug, label) in enumerate(ETHICAL_RISKS):
        entry = await repo.upsert_seed_entry(slug=slug, label=label, sort_order=order)
        print(f"  {entry.slug} ({entry.id})")

    print(f"Seeded {len(ETHICAL_RISKS)} ethical risk entries.")
    client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_run()))
