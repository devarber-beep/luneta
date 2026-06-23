"""Health check route."""
from fastapi import APIRouter

from app.settings import settings

router = APIRouter()


@router.get("", summary="Health check")
async def health() -> dict:
    return {"status": "ok", "web_url": settings.web_url}
