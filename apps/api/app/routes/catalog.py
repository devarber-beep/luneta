"""Read-only active catalog entries for scenario authoring."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db import get_db
from app.deps.authz import require_active_user_with_permission, require_any_active_permission
from app.domain.authz_permissions import Permission
from app.models.user import UserModel
from app.repositories.ethical_risks import EthicalRisksRepository
from app.repositories.scenario_classification import ScenarioClassificationRepository
from app.schemas.catalog import (
    ActiveClassificationListResponse,
    ActiveEthicalRiskListResponse,
    CatalogEntryPublic,
)

router = APIRouter()


@router.get("/scenario-classification", response_model=ActiveClassificationListResponse)
async def list_active_scenario_classification(
    db: AsyncIOMotorDatabase = Depends(get_db),
    _: UserModel = Depends(require_active_user_with_permission(Permission.SCENARIO_CREATE_DRAFT)),
) -> ActiveClassificationListResponse:
    repo = ScenarioClassificationRepository(db)
    await repo.ensure_indexes()
    entries = await repo.list_active()
    return ActiveClassificationListResponse(
        items=[CatalogEntryPublic(id=e.id or "", label=e.label) for e in entries]
    )


@router.get("/ethical-risks", response_model=ActiveEthicalRiskListResponse)
async def list_active_ethical_risks(
    db: AsyncIOMotorDatabase = Depends(get_db),
    _: UserModel = Depends(
        require_any_active_permission(
            Permission.SCENARIO_CREATE_DRAFT,
            Permission.SCENARIO_EVALUATE_PUBLISHED,
        )
    ),
) -> ActiveEthicalRiskListResponse:
    repo = EthicalRisksRepository(db)
    await repo.ensure_indexes()
    risks = await repo.list_active()
    return ActiveEthicalRiskListResponse(
        items=[CatalogEntryPublic(id=r.id or "", label=r.label) for r in risks]
    )
