"""Read-only active catalog entries for scenario authoring."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db import get_db
from app.deps.authz import require_any_active_permission
from app.domain.authz_permissions import Permission
from app.models.user import UserModel
from app.repositories.ethical_risks import EthicalRisksRepository
from app.schemas.catalog import ActiveEthicalRiskListResponse, CatalogEntryPublic

router = APIRouter()


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
