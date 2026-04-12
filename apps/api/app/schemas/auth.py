"""Auth API schemas for vertical slice."""
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: str = Field(pattern="^(author|reviewer)$")


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


class MeResponse(BaseModel):
    user_id: str
    email: EmailStr
    role: str
    is_email_verified: bool
