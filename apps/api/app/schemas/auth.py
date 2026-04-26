"""Auth API schemas for vertical slice."""
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: str = Field(pattern="^(investigator|coordinator)$")
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
    token_type: str = "bearer"


class ProfilePatchRequest(BaseModel):
    nickname: str = Field(min_length=2, max_length=40)
    first_name: str | None = Field(default=None, max_length=60)
    last_name: str | None = Field(default=None, max_length=60)


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
    email: EmailStr
    role: str
    is_email_verified: bool
    email_verified_at: datetime | None = None
    nickname: str
    first_name: str | None = None
    last_name: str | None = None
    avatar: AvatarResponse | None = None
    last_login_at: datetime | None = None
