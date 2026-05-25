"""Public routes for published scenarios."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db import get_db
from app.domain.enums import CollaboratorRole
from app.repositories.ethical_risks import EthicalRisksRepository
from app.repositories.scenario_classification import ScenarioClassificationRepository
from app.repositories.scenarios import ScenariosRepository
from app.repositories.users import UsersRepository
from app.schemas.public import (
    PublicCatalogLabel,
    PublicScenarioAsset,
    PublicScenarioListItem,
    PublicScenarioParticipant,
    PublicScenarioResponse,
)
from app.storage.minio_storage import MinioScenarioStorage

router = APIRouter()


async def _participants_for_scenario(
    *,
    scenario,
    users_repo: UsersRepository,
) -> tuple[str, list[PublicScenarioParticipant]]:
    author = await users_repo.get_by_id(scenario.author_user_id)
    author_nickname = author.nickname if author is not None else scenario.author_user_id
    collaborators: list[PublicScenarioParticipant] = []
    for collab in scenario.collaborators:
        if collab.role != CollaboratorRole.COLLABORATOR:
            continue
        user = await users_repo.get_by_id(collab.user_id)
        collaborators.append(
            PublicScenarioParticipant(
                user_id=collab.user_id,
                nickname=user.nickname if user is not None else collab.user_id,
            )
        )
    return author_nickname, collaborators


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


@router.get("/scenarios", response_model=list[PublicScenarioListItem])
async def list_public_scenarios(db: AsyncIOMotorDatabase = Depends(get_db)) -> list[PublicScenarioListItem]:
    repo = ScenariosRepository(db)
    scenarios = await repo.list_publicly_visible()
    return [
        PublicScenarioListItem(
            id=s.id or "",
            title=s.public_title or s.title,
            published_at=s.published_at or s.updated_at,
            public_path=f"/public/{s.public_slug}",
        )
        for s in scenarios
    ]


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
    author_nickname, collaborators = await _participants_for_scenario(
        scenario=scenario,
        users_repo=users_repo,
    )
    categories, ethical_risks = await _catalog_labels_for_scenario(scenario=scenario, db=db)
    return PublicScenarioResponse(
        id=scenario.id or "",
        author_user_id=scenario.author_user_id,
        author_nickname=author_nickname,
        title=scenario.public_title or scenario.title,
        description=scenario.public_description or scenario.description,
        summary=scenario.summary,
        published_at=scenario.published_at or scenario.updated_at,
        categories=categories,
        ethical_risks=ethical_risks,
        cover_image=cover,
        inline_assets=inline_assets,
        collaborators=collaborators,
    )
