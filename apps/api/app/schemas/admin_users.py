"""Request and response bodies for admin user management."""
from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.domain.enums import UserAccountStatus, UserRole


class AdminCreateInvestigatorRequest(BaseModel):
    email: EmailStr
    first_name: str = Field(min_length=1, max_length=60)
    last_name: str = Field(min_length=1, max_length=60)


class AdminCreateInvestigatorResponse(BaseModel):
    user_id: str
    email_normalized: EmailStr


class AdminSetUserRoleRequest(BaseModel):
    """Allowed transitions: registered → investigator; investigator → reviewer."""

    role: UserRole

    @field_validator("role")
    @classmethod
    def only_investigator_or_reviewer(cls, v: UserRole) -> UserRole:
        if v not in (UserRole.INVESTIGATOR, UserRole.REVIEWER):
            raise ValueError("role must be investigator or reviewer")
        return v


class AdminSetAccountStatusRequest(BaseModel):
    account_status: UserAccountStatus


class AdminUserMutationResponse(BaseModel):
    user_id: str
    role: UserRole
    account_status: UserAccountStatus


class ReviewerInvestigatorIdsResponse(BaseModel):
    reviewer_user_id: str
    investigator_user_ids: list[str]


class AdminUserSummaryResponse(BaseModel):
    user_id: str
    display_name: str
    email_normalized: EmailStr
    role: UserRole
