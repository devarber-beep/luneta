"""Ethical risk catalog entry for scenario evaluation."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class EthicalRiskEntryModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str | None = Field(default=None, alias="_id")
    slug: str = Field(min_length=1, max_length=80)
    label: str = Field(min_length=1, max_length=200)
    is_active: bool = True
    sort_order: int = 0
    created_at: datetime
    updated_at: datetime
