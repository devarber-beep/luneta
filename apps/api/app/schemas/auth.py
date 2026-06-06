"""Request and response bodies for authentication and profile endpoints."""
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, model_validator

from app.domain.enums import UserAccountStatus, UserRole


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    nickname: str = Field(min_length=2, max_length=40)


class SignupResponse(BaseModel):
    user_id: str
    requires_email_verification: bool = True


class DevLastEmailVerificationResponse(BaseModel):
    email: EmailStr
    token: str
    issued_at: datetime


class VerifyEmailRequest(BaseModel):
    token: str


class VerifyEmailResponse(BaseModel):
    verified: bool


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    must_change_password: bool = False
    token_type: str = "bearer"


class ProfilePatchRequest(BaseModel):
    nickname: str | None = Field(default=None, min_length=2, max_length=40)
    first_name: str | None = Field(default=None, max_length=60)
    last_name: str | None = Field(default=None, max_length=60)
    organization: str | None = Field(default=None, max_length=200)
    university: str | None = Field(default=None, max_length=200)
    biography: str | None = Field(default=None, max_length=4000)

    @model_validator(mode="after")
    def at_least_one_field(self) -> "ProfilePatchRequest":
        if not self.model_dump(exclude_unset=True):
            raise ValueError("At least one field must be provided")
        return self


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class MeResponse(BaseModel):
    class AvatarResponse(BaseModel):
        bucket: str
        object_key: str
        version_id: str | None = None
        content_type: str
        size_bytes: int
        updated_at: datetime

    user_id: str
    email_normalized: EmailStr
    role: UserRole
    account_status: UserAccountStatus
    email_verified_at: datetime | None = None
    must_change_password: bool = False
    nickname: str
    first_name: str | None = None
    last_name: str | None = None
    organization: str | None = None
    university: str | None = None
    biography: str | None = None
    avatar: AvatarResponse | None = None
    avatar_url: str | None = None
    last_login_at: datetime | None = None
