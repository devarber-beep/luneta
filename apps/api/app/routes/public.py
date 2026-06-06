"""Public routes for published scenarios."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db import get_db
from app.domain.enums import CollaboratorRole
from app.repositories.ethical_risks import EthicalRisksRepository
from app.repositories.scenario_classification import ScenarioClassificationRepository
from app.repositories.scenarios import ScenariosRepository
from app.repositories.users import UsersRepository
from app.schemas.public import (
    PublicCatalogLabel,
    PublicCatalogListResponse,
    PublicScenarioAsset,
    PublicScenarioListItem,
    PublicScenarioParticipant,
    PublicScenarioResponse,
    PublicScenarioSearchResponse,
)
from app.storage.minio_storage import MinioScenarioStorage

router = APIRouter()


def _author_display_name_for_scenario(*, scenario) -> str:
    if scenario.author_display_name:
        return scenario.author_display_name
    return scenario.author_user_id


async def _participants_for_scenario(
    *,
    scenario,
    users_repo: UsersRepository,
) -> tuple[str, list[PublicScenarioParticipant]]:
    author_display_name = _author_display_name_for_scenario(scenario=scenario)
    collaborators: list[PublicScenarioParticipant] = []
    for collab in scenario.collaborators:
        if collab.role != CollaboratorRole.COLLABORATOR:
            continue
        user = await users_repo.get_by_id(collab.user_id)
        collaborators.append(
            PublicScenarioParticipant(
                user_id=collab.user_id,
                display_name=user.display_name if user is not None else collab.user_id,
            )
        )
    return author_display_name, collaborators


async def _catalog_labels_for_scenario(*, scenario, db: AsyncIOMotorDatabase) -> tuple[list[PublicCatalogLabel], list[PublicCatalogLabel]]:
    classification_repo = ScenarioClassificationRepository(db)
    ethical_repo = EthicalRisksRepository(db)
    categories: list[PublicCatalogLabel] = []
    for cid in scenario.category_ids:
        row = await classification_repo.get_by_id(cid)
        if row is not None and row.is_active:
            categories.append(PublicCatalogLabel(id=cid, label=row.label))
    ethical_risks: list[PublicCatalogLabel] = []
    for rid in scenario.ethical_risk_ids:
        row = await ethical_repo.get_by_id(rid)
        if row is not None and row.is_active:
            ethical_risks.append(PublicCatalogLabel(id=rid, label=row.label))
    return categories, ethical_risks


async def _list_items_for_scenarios(
    *,
    scenarios,
) -> list[PublicScenarioListItem]:
    items: list[PublicScenarioListItem] = []
    for scenario in scenarios:
        items.append(
            PublicScenarioListItem(
                id=scenario.id or "",
                title=scenario.public_title or scenario.title,
                published_at=scenario.published_at or scenario.updated_at,
                public_path=f"/public/{scenario.public_slug}",
                author_user_id=scenario.author_user_id,
                author_display_name=_author_display_name_for_scenario(scenario=scenario),
                author_university=scenario.author_university,
            )
        )
    return items


@router.get("/catalog/categories", response_model=PublicCatalogListResponse)
async def list_public_search_categories(
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> PublicCatalogListResponse:
    repo = ScenarioClassificationRepository(db)
    await repo.ensure_indexes()
    entries = await repo.list_active()
    return PublicCatalogListResponse(
        items=[PublicCatalogLabel(id=e.id or "", label=e.label) for e in entries]
    )


@router.get("/catalog/ethical-risks", response_model=PublicCatalogListResponse)
async def list_public_search_ethical_risks(
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> PublicCatalogListResponse:
    repo = EthicalRisksRepository(db)
    await repo.ensure_indexes()
    risks = await repo.list_active()
    return PublicCatalogListResponse(
        items=[PublicCatalogLabel(id=r.id or "", label=r.label) for r in risks]
    )


@router.get("/scenarios", response_model=PublicScenarioSearchResponse)
async def search_public_scenarios(
    q: str | None = Query(default=None, max_length=200),
    author_user_id: str | None = Query(default=None),
    published_from: datetime | None = Query(default=None),
    published_to: datetime | None = Query(default=None),
    category_id: list[str] = Query(default=[]),
    ethical_risk_id: list[str] = Query(default=[]),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> PublicScenarioSearchResponse:
    users_repo = UsersRepository(db)
    trimmed_q = (q or "").strip()
    author_ids_from_name: list[str] = []
    if trimmed_q:
        author_ids_from_name = await users_repo.list_ids_matching_display_name(trimmed_q)

    repo = ScenariosRepository(db)
    scenarios, total = await repo.search_publicly_visible(
        q=q,
        q_matching_author_user_ids=author_ids_from_name or None,
        author_user_id=author_user_id,
        published_from=published_from,
        published_to=published_to,
        category_ids=category_id or None,
        ethical_risk_ids=ethical_risk_id or None,
        page=page,
        page_size=page_size,
    )
    items = await _list_items_for_scenarios(scenarios=scenarios)
    return PublicScenarioSearchResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/scenarios/{slug}", response_model=PublicScenarioResponse)
async def get_public_scenario(slug: str, db: AsyncIOMotorDatabase = Depends(get_db)) -> PublicScenarioResponse:
    repo = ScenariosRepository(db)
    users_repo = UsersRepository(db)
    scenario = await repo.get_by_public_slug(slug)
    if scenario is None or scenario.published_at is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")
    storage = MinioScenarioStorage.from_settings()
    cover: PublicScenarioAsset | None = None
    if scenario.cover_image is not None:
        cover = PublicScenarioAsset(
            asset_id=scenario.cover_image.asset_id,
            alt_text=scenario.cover_image.alt_text,
            mime_type=scenario.cover_image.mime_type,
            order=scenario.cover_image.order,
            signed_url=storage.presigned_get_url(storage_key=scenario.cover_image.storage_key, expires_seconds=900),
        )
    inline_assets = [
        PublicScenarioAsset(
            asset_id=asset.asset_id,
            alt_text=asset.alt_text,
            mime_type=asset.mime_type,
            order=asset.order,
            signed_url=storage.presigned_get_url(storage_key=asset.storage_key, expires_seconds=900),
        )
        for asset in sorted(scenario.inline_assets, key=lambda x: x.order)
    ]
    author_display_name, collaborators = await _participants_for_scenario(
        scenario=scenario,
        users_repo=users_repo,
    )
    categories, ethical_risks = await _catalog_labels_for_scenario(scenario=scenario, db=db)
    return PublicScenarioResponse(
        id=scenario.id or "",
        author_user_id=scenario.author_user_id,
        author_display_name=author_display_name,
        author_university=scenario.author_university,
        title=scenario.public_title or scenario.title,
        description=scenario.public_description or scenario.description,
        summary=scenario.summary,
        published_at=scenario.published_at or scenario.updated_at,
        categories=categories,
        ethical_risks=ethical_risks,
        usage_context=scenario.usage_context,
        cover_image=cover,
        inline_assets=inline_assets,
        collaborators=collaborators,
    )
