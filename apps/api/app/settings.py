"""Application settings from environment."""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Monorepo root `.env` (Luneta/), not `apps/api/.env`.
_REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    # Monorepo root `.env` may define keys for web, AI, etc.; ignore unknowns so API tests
    # work when pytest is run from repo root (`python -m pytest`) as well as from `apps/api`.
    model_config = SettingsConfigDict(env_file=_REPO_ROOT / ".env", extra="ignore")

    app_name: str = "Luneta API"
    api_url: str = "http://localhost:8000"

    mongodb_uri: str = "mongodb://localhost:27017/luneta"
    redis_url: str = "redis://localhost:6379/0"

    s3_endpoint: str = "http://localhost:9000"
    s3_public_endpoint: str = "http://localhost:9000"
    s3_region: str = "us-east-1"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket_luneta: str = "luneta-assets"

    web_url: str = "http://localhost:5173"
    email_from: str = "Luneta <no-reply@luneta.local>"
    email_smtp_host: str = "localhost"
    email_smtp_port: int = 1025
    # When true, SMTP errors are logged but do not fail API requests (recommended for dev/tests).
    email_fail_silently: bool = True
    email_verification_token_ttl_minutes: int = 60
    # When true, the last signup email verification token is kept in memory and exposed via
    # GET /auth/dev/last-email-verification. Never enable in production.
    dev_expose_last_email_verification_token: bool = False

    auth_token_secret: str = "change-me-in-env"
    auth_token_ttl_seconds: int = 3600

    openai_api_key: str | None = None
    openai_embedding_model: str = "text-embedding-3-small"

settings = Settings()
