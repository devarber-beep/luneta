"""Admin catalog management request and response bodies."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class CatalogEntryResponse(BaseModel):
    id: str
    label: str
    is_active: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime


class ClassificationCatalogListResponse(BaseModel):
    items: list[CatalogEntryResponse]


class CreateClassificationEntryRequest(BaseModel):
    label: str = Field(min_length=1, max_length=120)
    sort_order: int = 0


class PatchClassificationEntryRequest(BaseModel):
    label: str | None = Field(default=None, min_length=1, max_length=120)
    sort_order: int | None = None
    is_active: bool | None = None


class EthicalRiskEntryResponse(BaseModel):
    id: str
    label: str
    is_active: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime


class EthicalRiskCatalogListResponse(BaseModel):
    items: list[EthicalRiskEntryResponse]


class CreateEthicalRiskEntryRequest(BaseModel):
    label: str = Field(min_length=1, max_length=200)
    sort_order: int = 0


class PatchEthicalRiskEntryRequest(BaseModel):
    label: str | None = Field(default=None, min_length=1, max_length=200)
    sort_order: int | None = None
    is_active: bool | None = None
