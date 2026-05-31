"""HTTP tests for public scenario search (RF-7.1)."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from bson import ObjectId


def _public_items(payload: dict) -> list[dict]:
    return payload["items"]


async def _seed_published(
    fake_db,
    *,
    scenario_id: str,
    author_id: str,
    title: str,
    description: str,
    slug: str,
    published_at: datetime,
    category_ids: list[str] | None = None,
    ethical_risk_ids: list[str] | None = None,
) -> None:
    now = datetime.now(UTC)
    await fake_db["scenarios"].insert_one(
        {
            "_id": ObjectId(scenario_id),
            "slug": slug,
            "title": title,
            "description": description,
            "public_title": title,
            "public_description": description,
            "public_slug": slug,
            "author_user_id": author_id,
            "collaborators": [
                {
                    "user_id": author_id,
                    "role": "owner",
                    "added_at": now,
                    "added_by": author_id,
                }
            ],
            "state": "published",
            "category_ids": category_ids or [],
            "ethical_risk_ids": ethical_risk_ids or [],
            "keywords_normalized": [],
            "published_at": published_at,
            "last_state_changed_at": now,
            "created_at": now,
            "updated_at": now,
        }
    )


@pytest.mark.asyncio
async def test_public_catalog_filters_no_auth(api_client, fake_db) -> None:
    now = datetime.now(UTC)
    await fake_db["scenario_classification_catalog"].insert_one(
        {
            "slug": "pub-cat",
            "label": "Education",
            "is_active": True,
            "sort_order": 0,
            "created_at": now,
            "updated_at": now,
        }
    )
    await fake_db["ethical_risk_catalog"].insert_one(
        {
            "slug": "pub-risk",
            "label": "Privacy",
            "is_active": True,
            "sort_order": 0,
            "created_at": now,
            "updated_at": now,
        }
    )
    cats = await api_client.get("/public/catalog/categories")
    assert cats.status_code == 200
    assert len(cats.json()["items"]) == 1
    assert cats.json()["items"][0]["label"] == "Education"
    risks = await api_client.get("/public/catalog/ethical-risks")
    assert risks.status_code == 200
    assert risks.json()["items"][0]["label"] == "Privacy"


@pytest.mark.asyncio
async def test_public_search_text_filter_and_pagination(api_client, fake_db) -> None:
    now = datetime.now(UTC)
    author_id = str(ObjectId())
    await fake_db["users"].insert_one(
        {
            "_id": ObjectId(author_id),
            "email_normalized": "searchowner@luneta.dev",
            "nickname": "searchowner",
            "nickname_normalized": "searchowner",
            "role": "investigator",
            "password_hash": "x",
            "password_updated_at": now,
            "created_at": now,
            "updated_at": now,
        }
    )
    cat_id = str(ObjectId())
    await _seed_published(
        fake_db,
        scenario_id=str(ObjectId()),
        author_id=author_id,
        title="Smart glasses in classroom",
        description="Children use devices during lessons.",
        slug="classroom-glasses",
        published_at=now - timedelta(days=1),
        category_ids=[cat_id],
    )
    await _seed_published(
        fake_db,
        scenario_id=str(ObjectId()),
        author_id=author_id,
        title="Outdoor play study",
        description="Weekend activities without screens.",
        slug="outdoor-play",
        published_at=now,
    )

    all_rows = await api_client.get("/public/scenarios", params={"page_size": 10})
    assert all_rows.status_code == 200
    body = all_rows.json()
    assert body["total"] == 2
    assert len(_public_items(body)) == 2
    assert body["items"][0]["title"] == "Outdoor play study"

    text = await api_client.get("/public/scenarios", params={"q": "classroom"})
    assert text.status_code == 200
    assert text.json()["total"] == 1
    assert _public_items(text.json())[0]["title"] == "Smart glasses in classroom"
    assert _public_items(text.json())[0]["author_nickname"] == "searchowner"

    by_author = await api_client.get("/public/scenarios", params={"author_user_id": author_id})
    assert by_author.json()["total"] == 2

    by_nickname = await api_client.get("/public/scenarios", params={"q": "searchown"})
    assert by_nickname.status_code == 200
    assert by_nickname.json()["total"] == 2

    page = await api_client.get("/public/scenarios", params={"page": 1, "page_size": 1})
    assert page.json()["total"] == 2
    assert len(_public_items(page.json())) == 1
