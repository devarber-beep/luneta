"""Organizations router with real MongoDB access."""
from typing import Any, List

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db import get_db

router = APIRouter()


def _orgs_collection(db: AsyncIOMotorDatabase):
    return db["orgs"]


@router.get("", summary="List organizations")
async def list_orgs(db: AsyncIOMotorDatabase = Depends(get_db)) -> List[dict[str, Any]]:
    """
    Return all organizations from MongoDB.

    For now we return raw documents with `_id` serialized as string.
    """
    docs: list[dict[str, Any]] = []
    cursor = _orgs_collection(db).find({})
    async for doc in cursor:
        doc["_id"] = str(doc.get("_id"))
        docs.append(doc)
    return docs

