"""Persistence model for users collection."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.domain.enums import UserAccountStatus, UserRole


class UserAvatarModel(BaseModel):
    bucket: str
    object_key: str
    version_id: str | None = None
    content_type: str
    size_bytes: int
    updated_at: datetime


class UserModel(BaseModel):
    """``users`` document. Login and uniqueness use ``email_normalized``; verified when ``email_verified_at`` is set."""

    model_config = ConfigDict(populate_by_name=True)

    id: str | None = Field(default=None, alias="_id")
    email_normalized: EmailStr
    password_hash: str
    password_updated_at: datetime
    role: UserRole
    account_status: UserAccountStatus = UserAccountStatus.ACTIVE
    email_verified_at: datetime | None = None
    first_name: str = Field(min_length=1, max_length=60)
    last_name: str = Field(min_length=1, max_length=60)
    display_name: str = Field(min_length=1, max_length=121)
    display_name_normalized: str = Field(min_length=1, max_length=121)
    organization: str | None = Field(default=None, max_length=200)
    university: str | None = Field(default=None, max_length=200)
    university_normalized: str | None = Field(default=None, max_length=200)
    biography: str | None = Field(default=None, max_length=4000)
    avatar: UserAvatarModel | None = None
    must_change_password: bool = False
    last_login_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
