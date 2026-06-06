"""API schemas for ephemeral AI improvement suggestions to scenario authors."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

AiSuggestionScope = Literal["title", "description_full", "description_paragraph"]
AiSuggestionKind = Literal["clarity", "structure", "safety", "rewrite"]
AiSuggestionEmptyReason = Literal["none", "model_empty", "filtered"]


class AiSuggestionItemResponse(BaseModel):
    id: str
    scope: AiSuggestionScope
    kind: AiSuggestionKind
    paragraph_index: int | None = None
    current_excerpt: str
    proposed_text: str
    rationale: str


class AiSuggestionGenerateRequest(BaseModel):
    """Optional draft text from the editor (may differ from last saved revision)."""

    title: str | None = Field(default=None, max_length=500)
    description: str | None = Field(default=None, max_length=50000)


class AiSuggestionGenerateResponse(BaseModel):
    request_id: str
    items: list[AiSuggestionItemResponse]
    provider: str
    raw_items_received: int = 0
    empty_reason: AiSuggestionEmptyReason = "none"
    items_filtered_out: int = 0


class AiSuggestionActionRequest(BaseModel):
    request_id: str
    scope: AiSuggestionScope
    kind: AiSuggestionKind
    paragraph_index: int | None = None
    current_excerpt: str = Field(min_length=1, max_length=4000)
    proposed_text: str = Field(min_length=1, max_length=8000)
    rationale: str = Field(min_length=1, max_length=4000)


class AiSuggestionActionResponse(BaseModel):
    recorded: bool = True
