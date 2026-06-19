"""Shared helpers for scenario list cards (cover URL, text preview, evaluation stats)."""
from __future__ import annotations

from dataclasses import dataclass

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.domain.enums import EvaluationVisibility
from app.repositories.scenario_evaluations import ScenarioEvaluationsRepository
from app.storage.minio_storage import MinioScenarioStorage


@dataclass(frozen=True)
class EvaluationStatsPreview:
    evaluation_count: int = 0
    average_risk_score: float | None = None
    average_benefit_score: float | None = None


def description_preview(text: str | None, *, max_length: int = 180) -> str | None:
    if not text or not text.strip():
        return None
    normalized = " ".join(text.split())
    if len(normalized) <= max_length:
        return normalized
    return normalized[: max_length - 1].rstrip() + "…"


def cover_signed_url(
    scenario,
    storage: MinioScenarioStorage,
) -> tuple[str | None, str | None]:
    if scenario.cover_image is None:
        return None, None
    return (
        storage.presigned_get_url(
            storage_key=scenario.cover_image.storage_key,
            expires_seconds=900,
        ),
        scenario.cover_image.alt_text,
    )


async def evaluation_stats_for_scenario_ids(
    db: AsyncIOMotorDatabase,
    scenario_ids: list[str],
) -> dict[str, EvaluationStatsPreview]:
    if not scenario_ids:
        return {}
    collection = ScenarioEvaluationsRepository(db)._collection
    pipeline = [
        {
            "$match": {
                "scenario_id": {"$in": scenario_ids},
                "visibility": EvaluationVisibility.VISIBLE.value,
            }
        },
        {
            "$group": {
                "_id": "$scenario_id",
                "evaluation_count": {"$sum": 1},
                "average_risk_score": {"$avg": "$risk_score"},
                "average_benefit_score": {"$avg": "$benefit_score"},
            }
        },
    ]
    out: dict[str, EvaluationStatsPreview] = {}
    async for row in collection.aggregate(pipeline):
        scenario_id = row.get("_id")
        if not isinstance(scenario_id, str) or not scenario_id:
            continue
        count = int(row.get("evaluation_count", 0))
        avg_risk = row.get("average_risk_score")
        avg_benefit = row.get("average_benefit_score")
        out[scenario_id] = EvaluationStatsPreview(
            evaluation_count=count,
            average_risk_score=round(float(avg_risk), 2) if avg_risk is not None else None,
            average_benefit_score=round(float(avg_benefit), 2) if avg_benefit is not None else None,
        )
    return out
