"""Validation before a scenario may be submitted for review."""
from __future__ import annotations

from fastapi import HTTPException, status

from app.models.scenario import ScenarioModel
from app.repositories.ethical_risks import EthicalRisksRepository
from app.repositories.scenario_classification import ScenarioClassificationRepository


async def ensure_ready_for_submit(
    *,
    scenario: ScenarioModel,
    classification_repo: ScenarioClassificationRepository,
    ethical_repo: EthicalRisksRepository,
) -> None:
    missing: list[str] = []
    if not scenario.title.strip():
        missing.append("title")
    if not scenario.description.strip():
        missing.append("description")
    if scenario.cover_image is None:
        missing.append("cover_image")
    if not scenario.category_ids:
        missing.append("categories")
    if not scenario.ethical_risk_ids:
        missing.append("ethical_risks")
    ctx = scenario.usage_context
    if ctx is None or not ctx.is_complete():
        missing.append("usage_context")

    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot submit for review: missing {', '.join(missing)}",
        )

    active_categories = {e.id for e in await classification_repo.list_active() if e.id}
    for category_id in scenario.category_ids:
        if category_id not in active_categories:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or inactive category selection",
            )

    active_risks = {e.id for e in await ethical_repo.list_active() if e.id}
    for risk_id in scenario.ethical_risk_ids:
        if risk_id not in active_risks:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or inactive ethical risk selection",
            )
