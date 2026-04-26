"""Persistence model for users collection."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.domain.enums import UserRole


class UserAvatarModel(BaseModel):
    bucket: str
    object_key: str
    version_id: str | None = None
    content_type: str
    size_bytes: int
    updated_at: datetime


class UserModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str | None = Field(default=None, alias="_id")
    email: EmailStr
    email_normalized: str
    password_hash: str
    password_updated_at: datetime
    role: UserRole
    is_email_verified: bool = False
    email_verified_at: datetime | None = None
    nickname: str = Field(min_length=2, max_length=40)
    nickname_normalized: str
    first_name: str | None = Field(default=None, max_length=60)
    last_name: str | None = Field(default=None, max_length=60)
    avatar: UserAvatarModel | None = None
    last_login_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
