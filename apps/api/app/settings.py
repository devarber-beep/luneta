"""Application settings from environment."""
from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env")

    app_name: str = "Luneta API"
    api_url: str = "http://localhost:8000"

    mongodb_uri: str = "mongodb://localhost:27017/luneta"
    redis_url: str = "redis://localhost:6379/0"

    s3_endpoint: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket_luneta: str = "luneta-assets"

    email_smtp_host: str = "localhost"
    email_smtp_port: int = 1025
    email_verification_token_ttl_minutes: int = 60

    auth_token_secret: str = "change-me-in-env"
    auth_token_ttl_seconds: int = 3600

settings = Settings()
