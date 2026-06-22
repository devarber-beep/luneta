"""Application settings from environment."""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _optional_env_file() -> Path | None:
    """First `.env` found walking up from this module (monorepo root in local dev).

    In Docker the API image is `/app/app/`; compose injects vars via `env_file`, so no
    on-disk `.env` is required inside the container.
    """
    here = Path(__file__).resolve()
    for directory in (here.parent, *here.parents):
        candidate = directory / ".env"
        if candidate.is_file():
            return candidate
    return None


_env_file = _optional_env_file()
_settings_config = (
    SettingsConfigDict(extra="ignore", env_file=_env_file) if _env_file else SettingsConfigDict(extra="ignore")
)


class Settings(BaseSettings):
    # Monorepo root `.env` may define keys for web, AI, etc.; ignore unknowns so API tests
    # work when pytest is run from repo root (`python -m pytest`) as well as from `apps/api`.
    model_config = _settings_config

    mongodb_uri: str = "mongodb://localhost:27017/luneta"

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
    email_smtp_user: str | None = None
    email_smtp_password: str | None = None
    # When set, outbound mail uses Brevo HTTPS API (required on Render free tier; SMTP is blocked).
    brevo_api_key: str | None = None
    # When true, SMTP errors are logged but do not fail API requests (recommended for dev/tests).
    email_fail_silently: bool = True
    email_verification_token_ttl_minutes: int = 60
    # When true, the last signup email verification token is kept in memory and exposed via
    # GET /auth/dev/last-email-verification. Never enable in production.
    dev_expose_last_email_verification_token: bool = False

    auth_token_secret: str = "change-me-in-env"
    auth_token_ttl_seconds: int = 3600

    ai_provider: str = "gemini"
    gemini_api_key: str | None = None
    gemini_chat_model: str = "gemini-2.5-flash-lite"
    gemini_embedding_model: str = "gemini-embedding-001"
    openai_api_key: str | None = None
    openai_embedding_model: str = "text-embedding-3-small"
    openai_chat_model: str = "gpt-4o-mini"
    ai_suggestion_generations_per_hour: int = 5

    scenario_similarity_heuristic_min_score: float = 0.88
    scenario_similarity_embedding_min_score: float = 0.88
    scenario_similarity_min_shared_tokens: int = 6


settings = Settings()
