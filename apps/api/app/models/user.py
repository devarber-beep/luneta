"""Persistence model for users collection."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.domain.enums import UserRole


class UserModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str | None = Field(default=None, alias="_id")
    email: EmailStr
    password_hash: str
    role: UserRole
    is_email_verified: bool = False
    created_at: datetime
    updated_at: datetime
