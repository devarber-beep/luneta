from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Luneta API"
    api_url: str = "http://localhost:8000"

    mongodb_uri: str = "mongodb://localhost:27017/luneta"
    redis_url: str = "redis://localhost:6379/0"

    s3_endpoint: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket_luneta: str = "luneta-assets"

    email_from: str = "Luneta <no-reply@luneta.local>"
    email_smtp_host: str = "localhost"
    email_smtp_port: int = 1025

    ai_provider: str = "openai"
    ai_model: str = "gpt-4.1-mini"

    class Config:
        env_file = ".env"


settings = Settings()

