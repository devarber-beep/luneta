"""Injectable storage adapters (MinIO)."""
from __future__ import annotations

from app.storage.minio_storage import MinioUserAvatarStorage


def get_user_avatar_storage() -> MinioUserAvatarStorage:
    return MinioUserAvatarStorage.from_settings()
