"""Public routes for published scenarios."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db import get_db
from app.domain.enums import ScenarioState
from app.repositories.scenarios import ScenariosRepository
from app.schemas.public import PublicScenarioResponse

router = APIRouter()


@router.get("/scenarios/{slug}", response_model=PublicScenarioResponse)
async def get_public_scenario(slug: str, db: AsyncIOMotorDatabase = Depends(get_db)) -> PublicScenarioResponse:
    repo = ScenariosRepository(db)
    scenario = await repo.get_by_slug_and_state(slug=slug, state=ScenarioState.PUBLISHED)
    if scenario is None or scenario.published_at is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")
    return PublicScenarioResponse(
        slug=scenario.slug,
        title=scenario.title,
        body_markdown=scenario.body_markdown,
        published_at=scenario.published_at,
    )
