"""Persistence model for email verification tokens collection."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class EmailVerificationTokenModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str | None = Field(default=None, alias="_id")
    user_id: str
    email: EmailStr
    token_hash: str
    expires_at: datetime
    consumed_at: datetime | None = None
    created_at: datetime
