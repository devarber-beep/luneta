"""Public read-only schemas for published scenarios."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.scenario_usage_context import ScenarioUsageContextModel

class PublicScenarioListItem(BaseModel):
    id: str
    title: str
    published_at: datetime
    public_path: str
    author_user_id: str
    author_nickname: str
    author_university: str | None = None


class PublicScenarioSearchResponse(BaseModel):
    items: list[PublicScenarioListItem]
    total: int
    page: int
    page_size: int


class PublicScenarioAsset(BaseModel):
    asset_id: str
    alt_text: str | None = None
    mime_type: str
    order: int
    signed_url: str


class PublicScenarioParticipant(BaseModel):
    user_id: str
    nickname: str


class PublicCatalogLabel(BaseModel):
    id: str
    label: str


class PublicCatalogListResponse(BaseModel):
    items: list[PublicCatalogLabel]


class PublicScenarioResponse(BaseModel):
    id: str
    author_user_id: str
    author_nickname: str
    author_university: str | None = None
    title: str
    description: str
    summary: str | None = None
    published_at: datetime
    categories: list[PublicCatalogLabel] = Field(default_factory=list)
    ethical_risks: list[PublicCatalogLabel] = Field(default_factory=list)
    usage_context: ScenarioUsageContextModel | None = None
    cover_image: PublicScenarioAsset | None = None
    inline_assets: list[PublicScenarioAsset] = Field(default_factory=list)
    collaborators: list[PublicScenarioParticipant] = Field(default_factory=list)
