"""Public read-only schemas for published scenarios."""
from datetime import datetime

from pydantic import BaseModel


class PublicScenarioResponse(BaseModel):
    slug: str
    title: str
    body_markdown: str
    published_at: datetime
