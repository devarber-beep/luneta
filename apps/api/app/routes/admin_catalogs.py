"""Admin routes for editable catalogs (scenario classification, ethical risks)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.errors import DuplicateKeyError

from app.db import get_db
from app.deps.authz import require_permission
from app.domain.authz_permissions import Permission
from app.models.user import UserModel
from app.core.catalog_slugs import allocate_unique_catalog_slug, slug_from_label
from app.repositories.ethical_risks import EthicalRisksRepository
from app.repositories.scenario_classification import ScenarioClassificationRepository
from app.schemas.admin_catalogs import (
    CatalogEntryResponse,
    ClassificationCatalogListResponse,
    CreateClassificationEntryRequest,
    CreateEthicalRiskEntryRequest,
    EthicalRiskCatalogListResponse,
    EthicalRiskEntryResponse,
    PatchClassificationEntryRequest,
    PatchEthicalRiskEntryRequest,
)

router = APIRouter()


def _classification_response(entry) -> CatalogEntryResponse:
    return CatalogEntryResponse(
        id=entry.id or "",
        label=entry.label,
        is_active=entry.is_active,
        sort_order=entry.sort_order,
        created_at=entry.created_at,
        updated_at=entry.updated_at,
    )


def _ethical_risk_response(entry) -> EthicalRiskEntryResponse:
    return EthicalRiskEntryResponse(
        id=entry.id or "",
        label=entry.label,
        is_active=entry.is_active,
        sort_order=entry.sort_order,
        created_at=entry.created_at,
        updated_at=entry.updated_at,
    )


@router.get("/catalog/scenario-classification", response_model=ClassificationCatalogListResponse)
async def list_scenario_classification_catalog(
    db: AsyncIOMotorDatabase = Depends(get_db),
    _: UserModel = Depends(require_permission(Permission.USER_ADMIN_MANAGE_SCENARIO_CLASSIFICATION)),
) -> ClassificationCatalogListResponse:
    repo = ScenarioClassificationRepository(db)
    await repo.ensure_indexes()
    items = await repo.list_all()
    return ClassificationCatalogListResponse(items=[_classification_response(e) for e in items])


@router.post(
    "/catalog/scenario-classification",
    response_model=CatalogEntryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_scenario_classification_entry(
    payload: CreateClassificationEntryRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    _: UserModel = Depends(require_permission(Permission.USER_ADMIN_MANAGE_SCENARIO_CLASSIFICATION)),
) -> CatalogEntryResponse:
    repo = ScenarioClassificationRepository(db)
    await repo.ensure_indexes()
    base_slug = slug_from_label(payload.label)
    slug = await allocate_unique_catalog_slug(get_by_slug=repo.get_by_slug, base_slug=base_slug)
    try:
        entry = await repo.create_entry(
            slug=slug,
            label=payload.label,
            sort_order=payload.sort_order,
        )
    except DuplicateKeyError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Could not create entry") from None
    return _classification_response(entry)


@router.patch("/catalog/scenario-classification/{entry_id}", response_model=CatalogEntryResponse)
async def patch_scenario_classification_entry(
    entry_id: str,
    payload: PatchClassificationEntryRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    _: UserModel = Depends(require_permission(Permission.USER_ADMIN_MANAGE_SCENARIO_CLASSIFICATION)),
) -> CatalogEntryResponse:
    raw = payload.model_dump(exclude_unset=True)
    if not raw:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")
    repo = ScenarioClassificationRepository(db)
    updated = await repo.update_entry(
        entry_id,
        label=raw.get("label"),
        sort_order=raw.get("sort_order"),
        is_active=raw.get("is_active"),
    )
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found")
    return _classification_response(updated)


@router.get("/catalog/ethical-risks", response_model=EthicalRiskCatalogListResponse)
async def list_ethical_risk_catalog(
    db: AsyncIOMotorDatabase = Depends(get_db),
    _: UserModel = Depends(require_permission(Permission.USER_ADMIN_MANAGE_ETHICAL_RISK_CATALOG)),
) -> EthicalRiskCatalogListResponse:
    repo = EthicalRisksRepository(db)
    await repo.ensure_indexes()
    items = await repo.list_all()
    return EthicalRiskCatalogListResponse(items=[_ethical_risk_response(e) for e in items])


@router.post(
    "/catalog/ethical-risks",
    response_model=EthicalRiskEntryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_ethical_risk_entry(
    payload: CreateEthicalRiskEntryRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    _: UserModel = Depends(require_permission(Permission.USER_ADMIN_MANAGE_ETHICAL_RISK_CATALOG)),
) -> EthicalRiskEntryResponse:
    repo = EthicalRisksRepository(db)
    await repo.ensure_indexes()
    base_slug = slug_from_label(payload.label)
    slug = await allocate_unique_catalog_slug(get_by_slug=repo.get_by_slug, base_slug=base_slug)
    try:
        entry = await repo.create_entry(slug=slug, label=payload.label, sort_order=payload.sort_order)
    except DuplicateKeyError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Could not create entry") from None
    return _ethical_risk_response(entry)


@router.patch("/catalog/ethical-risks/{entry_id}", response_model=EthicalRiskEntryResponse)
async def patch_ethical_risk_entry(
    entry_id: str,
    payload: PatchEthicalRiskEntryRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    _: UserModel = Depends(require_permission(Permission.USER_ADMIN_MANAGE_ETHICAL_RISK_CATALOG)),
) -> EthicalRiskEntryResponse:
    raw = payload.model_dump(exclude_unset=True)
    if not raw:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")
    repo = EthicalRisksRepository(db)
    updated = await repo.update_entry(
        entry_id,
        label=raw.get("label"),
        sort_order=raw.get("sort_order"),
        is_active=raw.get("is_active"),
    )
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found")
    return _ethical_risk_response(updated)
