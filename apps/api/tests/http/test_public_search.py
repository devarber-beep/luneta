"""HTTP tests for public scenario search."""
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
    author_display_name: str | None = None,
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
            "author_display_name": author_display_name,
            "author_display_name_normalized": author_display_name.lower() if author_display_name else None,
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
    display = "Searchowner User"
    await fake_db["users"].insert_one(
        {
            "_id": ObjectId(author_id),
            "email_normalized": "searchowner@luneta.dev",
            "first_name": "Searchowner",
            "last_name": "User",
            "display_name": display,
            "display_name_normalized": display.lower(),
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
        author_display_name=display,
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
        author_display_name=display,
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
    assert _public_items(text.json())[0]["author_display_name"] == display

    by_author = await api_client.get("/public/scenarios", params={"author_user_id": author_id})
    assert by_author.json()["total"] == 2

    by_name = await api_client.get("/public/scenarios", params={"q": "searchown"})
    assert by_name.status_code == 200
    assert by_name.json()["total"] == 2

    page = await api_client.get("/public/scenarios", params={"page": 1, "page_size": 1})
    assert page.json()["total"] == 2
    assert len(_public_items(page.json())) == 1


@pytest.mark.asyncio
async def test_public_search_university_text(api_client, fake_db) -> None:
    now = datetime.now(UTC)
    uabc = str(ObjectId())
    uxyz = str(ObjectId())
    await fake_db["users"].insert_one(
        {
            "_id": ObjectId(uabc),
            "email_normalized": "abc@luneta.dev",
            "first_name": "Author",
            "last_name": "Abc",
            "display_name": "Author Abc",
            "display_name_normalized": "author abc",
            "university": "University of ABC",
            "university_normalized": "university of abc",
            "role": "investigator",
            "password_hash": "x",
            "password_updated_at": now,
            "created_at": now,
            "updated_at": now,
        }
    )
    await fake_db["users"].insert_one(
        {
            "_id": ObjectId(uxyz),
            "email_normalized": "xyz@luneta.dev",
            "first_name": "Author",
            "last_name": "Xyz",
            "display_name": "Author Xyz",
            "display_name_normalized": "author xyz",
            "university": "University of XYZ",
            "university_normalized": "university of xyz",
            "role": "investigator",
            "password_hash": "x",
            "password_updated_at": now,
            "created_at": now,
            "updated_at": now,
        }
    )
    await _seed_published(
        fake_db,
        scenario_id=str(ObjectId()),
        author_id=uabc,
        title="ABC campus study",
        description="Research at ABC.",
        slug="abc-campus",
        published_at=now,
        author_display_name="Author Abc",
    )
    await _seed_published(
        fake_db,
        scenario_id=str(ObjectId()),
        author_id=uxyz,
        title="XYZ field trip",
        description="Research at XYZ.",
        slug="xyz-trip",
        published_at=now,
        author_display_name="Author Xyz",
    )
    await fake_db["scenarios"].update_many(
        {"author_user_id": uabc},
        {"$set": {"author_university": "University of ABC", "author_university_normalized": "university of abc"}},
    )
    await fake_db["scenarios"].update_many(
        {"author_user_id": uxyz},
        {"$set": {"author_university": "University of XYZ", "author_university_normalized": "university of xyz"}},
    )

    by_text = await api_client.get("/public/scenarios", params={"q": "University of ABC"})
    assert by_text.status_code == 200
    assert by_text.json()["total"] == 1
    assert _public_items(by_text.json())[0]["title"] == "ABC campus study"
    assert _public_items(by_text.json())[0]["author_university"] == "University of ABC"

    by_text_xyz = await api_client.get("/public/scenarios", params={"q": "University of XYZ"})
    assert by_text_xyz.status_code == 200
    assert by_text_xyz.json()["total"] == 1
