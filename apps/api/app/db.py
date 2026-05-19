"""Database connection (MongoDB)."""
from motor.motor_asyncio import AsyncIOMotorClient

from app.settings import settings

_client: AsyncIOMotorClient | None = None


def reset_client() -> None:
    """Drop the Motor singleton (tests with per-test event loops must call after each case)."""
    global _client
    if _client is not None:
        _client.close()
    _client = None


async def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(settings.mongodb_uri)
    return _client


async def get_db():
    client = await get_client()
    return client.get_default_database()
