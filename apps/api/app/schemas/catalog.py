"""Public catalog schemas for scenario authoring."""
from __future__ import annotations

from pydantic import BaseModel


class CatalogEntryPublic(BaseModel):
    id: str
    label: str


class ActiveEthicalRiskListResponse(BaseModel):
    items: list[CatalogEntryPublic]
