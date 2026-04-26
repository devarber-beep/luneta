"""Public routes for published scenarios."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db import get_db
from app.repositories.scenarios import ScenariosRepository
from app.schemas.public import PublicScenarioAsset, PublicScenarioListItem, PublicScenarioResponse
from app.storage.minio_storage import MinioScenarioStorage

router = APIRouter()


@router.get("/scenarios", response_model=list[PublicScenarioListItem])
async def list_public_scenarios(db: AsyncIOMotorDatabase = Depends(get_db)) -> list[PublicScenarioListItem]:
    repo = ScenariosRepository(db)
    scenarios = await repo.list_publicly_visible()
    return [
        PublicScenarioListItem(
            id=s.id or "",
            slug=s.public_slug,
            title=s.public_title,
            published_at=s.published_at or s.updated_at,
        )
        for s in scenarios
    ]


@router.get("/scenarios/{slug}", response_model=PublicScenarioResponse)
async def get_public_scenario(slug: str, db: AsyncIOMotorDatabase = Depends(get_db)) -> PublicScenarioResponse:
    repo = ScenariosRepository(db)
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
    return PublicScenarioResponse(
        id=scenario.id or "",
        slug=scenario.public_slug,
        title=scenario.public_title,
        body_markdown=scenario.public_body_markdown,
        published_at=scenario.published_at or scenario.updated_at,
        cover_image=cover,
        inline_assets=inline_assets,
    )
