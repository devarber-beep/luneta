"""MinIO storage adapter for scenario images."""
from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from datetime import timedelta
from urllib.parse import urlparse
from uuid import uuid4

from minio import Minio

from app.models.scenario import ScenarioAssetModel
from app.settings import settings


@dataclass
class MinioScenarioStorage:
    client: Minio
    public_client: Minio
    bucket: str

    @classmethod
    def from_settings(cls) -> "MinioScenarioStorage":
        client = cls._build_client(settings.s3_endpoint)
        public_client = cls._build_client(settings.s3_public_endpoint)
        return cls(client=client, public_client=public_client, bucket=settings.s3_bucket_luneta)

    @staticmethod
    def _build_client(endpoint: str) -> Minio:
        parsed = urlparse(endpoint)
        host = parsed.netloc or parsed.path
        secure = parsed.scheme == "https"
        return Minio(
            host,
            access_key=settings.s3_access_key,
            secret_key=settings.s3_secret_key,
            secure=secure,
            region=settings.s3_region,
        )

    def ensure_bucket(self) -> None:
        if not self.client.bucket_exists(self.bucket):
            self.client.make_bucket(self.bucket)

    def upload_image(
        self,
        *,
        scenario_id: str,
        scope: str,
        content: bytes,
        content_type: str,
        alt_text: str | None,
        order: int,
    ) -> ScenarioAssetModel:
        asset_id = str(uuid4())
        object_name = f"scenarios/{scenario_id}/{scope}/{asset_id}"
        self.client.put_object(
            self.bucket,
            object_name,
            data=BytesIO(content),
            length=len(content),
            content_type=content_type,
        )
        return ScenarioAssetModel(
            asset_id=asset_id,
            storage_key=object_name,
            url=None,
            alt_text=alt_text,
            width=None,
            height=None,
            mime_type=content_type,
            order=order,
        )

    def delete_object(self, *, storage_key: str) -> None:
        self.client.remove_object(self.bucket, storage_key)

    def presigned_get_url(self, *, storage_key: str, expires_seconds: int = 900) -> str:
        expiry = timedelta(seconds=max(60, min(expires_seconds, 7 * 24 * 3600)))
        return self.public_client.presigned_get_object(self.bucket, storage_key, expires=expiry)
