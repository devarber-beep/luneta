"""Public read-only schemas for published scenarios."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class PublicScenarioListItem(BaseModel):
    id: str
    slug: str
    title: str
    published_at: datetime


class PublicScenarioAsset(BaseModel):
    asset_id: str
    alt_text: str | None = None
    mime_type: str
    order: int
    signed_url: str


class PublicScenarioResponse(BaseModel):
    id: str
    slug: str
    title: str
    body_markdown: str
    published_at: datetime
    cover_image: PublicScenarioAsset | None = None
    inline_assets: list[PublicScenarioAsset] = Field(default_factory=list)
