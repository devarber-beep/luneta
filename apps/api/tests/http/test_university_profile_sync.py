"""HTTP tests for university on profile and scenario denormalization."""
from __future__ import annotations

from datetime import UTC, datetime

import pytest
from bson import ObjectId

from tests.conftest import user_doc


@pytest.mark.asyncio
async def test_patch_profile_university_syncs_author_scenarios(api_client, fake_db) -> None:
    now = datetime.now(UTC)
    inserted = await fake_db["users"].insert_one(
        user_doc(email="uniowner@luneta.dev", role="investigator", nickname="uniowner", verified=True)
    )
    user_id = str(inserted.inserted_id)
    scenario_id = str(ObjectId())
    await fake_db["scenarios"].insert_one(
        {
            "_id": ObjectId(scenario_id),
            "slug": "draft-uni",
            "title": "Draft with university",
            "description": "Body",
            "author_user_id": user_id,
            "collaborators": [
                {
                    "user_id": user_id,
                    "role": "owner",
                    "added_at": now,
                    "added_by": user_id,
                }
            ],
            "state": "draft",
            "category_ids": [],
            "ethical_risk_ids": [],
            "keywords_normalized": [],
            "last_state_changed_at": now,
            "created_at": now,
            "updated_at": now,
        }
    )

    login = await api_client.post(
        "/auth/login",
        json={"email": "uniowner@luneta.dev", "password": "UserPass123!"},
    )
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    patch = await api_client.patch(
        "/auth/me",
        headers=headers,
        json={"university": "  Open University  "},
    )
    assert patch.status_code == 200
    assert patch.json()["university"] == "Open University"

    doc = await fake_db["scenarios"].find_one({"_id": ObjectId(scenario_id)})
    assert doc is not None
    assert doc["author_university"] == "Open University"
    assert doc["author_university_normalized"] == "open university"
