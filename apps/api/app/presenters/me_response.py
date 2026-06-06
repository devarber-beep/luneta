"""Build MeResponse from a persisted user."""
from __future__ import annotations

from app.models.user import UserModel
from app.schemas.auth import MeResponse
from app.storage.minio_storage import MinioUserAvatarStorage


def build_me_response(*, user: UserModel, storage: MinioUserAvatarStorage) -> MeResponse:
    avatar_url = None
    if user.avatar is not None:
        avatar_url = storage.presigned_get_url(object_key=user.avatar.object_key)
    return MeResponse(
        user_id=user.id or "",
        email_normalized=user.email_normalized,
        role=user.role,
        account_status=user.account_status,
        email_verified_at=user.email_verified_at,
        must_change_password=user.must_change_password,
        first_name=user.first_name,
        last_name=user.last_name,
        display_name=user.display_name,
        organization=user.organization,
        university=user.university,
        biography=user.biography,
        avatar=MeResponse.AvatarResponse(**user.avatar.model_dump()) if user.avatar else None,
        avatar_url=avatar_url,
        last_login_at=user.last_login_at,
    )
