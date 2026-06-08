"""Validation before a scenario may be submitted for review."""
from __future__ import annotations

from fastapi import HTTPException, status

from app.models.scenario import ScenarioModel
from app.repositories.ethical_risks import EthicalRisksRepository
from app.repositories.scenario_classification import ScenarioClassificationRepository


async def _active_catalog_id_sets(
    *,
    classification_repo: ScenarioClassificationRepository,
    ethical_repo: EthicalRisksRepository,
) -> tuple[set[str], set[str]]:
    active_categories = {e.id for e in await classification_repo.list_active() if e.id}
    active_risks = {e.id for e in await ethical_repo.list_active() if e.id}
    return active_categories, active_risks


def filter_active_catalog_ids(
    *,
    category_ids: list[str],
    ethical_risk_ids: list[str],
    active_categories: set[str],
    active_risks: set[str],
) -> tuple[list[str], list[str]]:
    return (
        [category_id for category_id in category_ids if category_id in active_categories],
        [risk_id for risk_id in ethical_risk_ids if risk_id in active_risks],
    )


async def resolve_catalog_ids_for_save(
    *,
    scenario: ScenarioModel,
    category_ids: list[str] | None,
    ethical_risk_ids: list[str] | None,
    classification_repo: ScenarioClassificationRepository,
    ethical_repo: EthicalRisksRepository,
) -> tuple[list[str] | None, list[str] | None]:
    active_categories, active_risks = await _active_catalog_id_sets(
        classification_repo=classification_repo,
        ethical_repo=ethical_repo,
    )
    effective_category_ids, effective_ethical_risk_ids = filter_active_catalog_ids(
        category_ids=category_ids if category_ids is not None else scenario.category_ids,
        ethical_risk_ids=ethical_risk_ids if ethical_risk_ids is not None else scenario.ethical_risk_ids,
        active_categories=active_categories,
        active_risks=active_risks,
    )
    category_ids_for_update = (
        effective_category_ids
        if category_ids is not None or effective_category_ids != scenario.category_ids
        else None
    )
    ethical_risk_ids_for_update = (
        effective_ethical_risk_ids
        if ethical_risk_ids is not None or effective_ethical_risk_ids != scenario.ethical_risk_ids
        else None
    )
    return category_ids_for_update, ethical_risk_ids_for_update


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

