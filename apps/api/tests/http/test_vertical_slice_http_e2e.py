"""HTTP integration test for the vertical slice happy path."""
from __future__ import annotations

import os
from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from bson import ObjectId


def _use_real_mongo() -> bool:
    return os.environ.get("LUNETA_TEST_REAL_DB", "").strip().lower() in ("1", "true", "yes")


def _queue_row_for_scenario(items: list[dict], scenario_id: str) -> dict:
    matches = [i for i in items if i.get("scenario_id") == scenario_id]
    assert len(matches) == 1, matches
    return matches[0]


def _public_catalog_items(payload: dict | list) -> list[dict]:
    if isinstance(payload, dict):
        return payload["items"]
    return payload


def _public_catalog_row_for(rows: list[dict] | dict, *, scenario_id: str) -> dict:
    items = _public_catalog_items(rows) if isinstance(rows, dict) else rows
    matches = [r for r in items if r.get("id") == scenario_id]
    assert len(matches) == 1, matches
    return matches[0]


def _slug_from_public_path(public_path: str) -> str:
    prefix = "/public/"
    assert public_path.startswith(prefix), public_path
    return public_path[len(prefix) :]


async def _set_user_role(fake_db, *, email: str, role: str) -> None:
    await fake_db["users"].update_one(
        {"email_normalized": email.strip().lower()},
        {"$set": {"role": role}},
    )


async def _assign_reviewer_portfolio(
    fake_db, *, reviewer_user_id: str, investigator_user_id: str
) -> None:
    await fake_db["reviewer_assignments"].insert_one(
        {
            "reviewer_user_id": reviewer_user_id,
            "investigator_user_id": investigator_user_id,
            "created_at": datetime.now(UTC),
        }
    )


@pytest.mark.asyncio
async def test_vertical_slice_http_happy_path(api_client, fake_db):
    verify_token = "test-verify-token"

    with patch("app.services.email_verification_service.secrets.token_urlsafe", return_value=verify_token):
        signup_author = await api_client.post(
            "/auth/signup",
            json={
                "email": "author@luneta.dev",
                "password": "Password123!",
                "nickname": "author",
            },
        )
        assert signup_author.status_code == 200
        author_user_id = signup_author.json()["user_id"]

        verify_author = await api_client.post("/auth/verify-email", json={"token": verify_token})
        assert verify_author.status_code == 200
        assert verify_author.json()["verified"] is True

    await _set_user_role(fake_db, email="author@luneta.dev", role="investigator")

    login_author = await api_client.post(
        "/auth/login",
        json={
            "email": "author@luneta.dev",
            "password": "Password123!",
        },
    )
    assert login_author.status_code == 200
    author_token = login_author.json()["access_token"]
    author_headers = {"Authorization": f"Bearer {author_token}"}

    patch_profile = await api_client.patch(
        "/auth/me",
        json={"nickname": "author", "first_name": "Test", "last_name": "Author"},
        headers=author_headers,
    )
    assert patch_profile.status_code == 200
    assert patch_profile.json()["first_name"] == "Test"
    assert patch_profile.json()["last_name"] == "Author"

    create = await api_client.post(
        "/scenarios",
        json={
            "title": "Escenario E2E",
            "description": "E2E scenario description for reviewers",
        },
        headers=author_headers,
    )
    assert create.status_code == 200
    scenario_id = create.json()["id"]
    assert create.json()["author_user_id"] == author_user_id
    assert create.json()["state"] == "draft"

    mine = await api_client.get("/scenarios/mine", headers=author_headers)
    assert mine.status_code == 200
    assert len(mine.json()) == 1
    assert mine.json()[0]["title"] == "Escenario E2E"

    patch_draft = await api_client.patch(
        f"/scenarios/{scenario_id}",
        json={"description": "E2E scenario description updated"},
        headers=author_headers,
    )
    assert patch_draft.status_code == 200
    assert patch_draft.json()["current_revision_number"] == 2

    now = datetime.now(UTC)
    cat = await fake_db["scenario_classification_catalog"].insert_one(
        {
            "slug": "e2e-cat",
            "label": "E2E Category",
            "is_active": True,
            "sort_order": 0,
            "created_at": now,
            "updated_at": now,
        }
    )
    cat_id = str(cat.inserted_id)
    risk = await fake_db["ethical_risk_catalog"].insert_one(
        {
            "slug": "e2e-risk",
            "label": "E2E Risk",
            "is_active": True,
            "sort_order": 0,
            "created_at": now,
            "updated_at": now,
        }
    )
    risk_id = str(risk.inserted_id)

    if not _use_real_mongo():
        await fake_db["scenarios"].update_one(
            {"_id": ObjectId(scenario_id)},
            {
                "$set": {
                    "cover_image": {
                        "asset_id": "cover-e2e",
                        "storage_key": f"scenarios/{scenario_id}/cover/cover-e2e",
                        "mime_type": "image/png",
                        "order": 0,
                    }
                }
            },
        )
    else:
        cover_upload = await api_client.post(
            f"/scenarios/{scenario_id}/assets/cover",
            headers=author_headers,
            files={"file": ("cover.png", b"\x89PNG\r\n\x1a\n", "image/png")},
        )
        assert cover_upload.status_code == 200

    meta_patch = await api_client.patch(
        f"/scenarios/{scenario_id}",
        json={
            "category_ids": [cat_id],
            "ethical_risk_ids": [risk_id],
            "usage_context": {
                "children_age_start": 5,
                "children_age_end": 9,
                "children_count": 12,
                "duration_frequency": "once_a_week",
                "physically_present": "yes",
                "online_present": "no",
                "execution_place_affects_scenario": "yes",
                "special_circumstances": "no",
                "consent_in_place": "yes",
            },
        },
        headers=author_headers,
    )
    assert meta_patch.status_code == 200

    submit = await api_client.post(
        f"/scenarios/{scenario_id}/submit-review",
        headers=author_headers,
    )
    assert submit.status_code == 200
    assert submit.json()["state"] == "queued"

    with patch("app.services.email_verification_service.secrets.token_urlsafe", return_value="reviewer-token"):
        signup_reviewer = await api_client.post(
            "/auth/signup",
            json={
                "email": "reviewer@luneta.dev",
                "password": "Password123!",
                "nickname": "reviewer",
            },
        )
        assert signup_reviewer.status_code == 200

        verify_reviewer = await api_client.post("/auth/verify-email", json={"token": "reviewer-token"})
        assert verify_reviewer.status_code == 200

    await _set_user_role(fake_db, email="reviewer@luneta.dev", role="reviewer")
    reviewer_doc = await fake_db["users"].find_one({"email_normalized": "reviewer@luneta.dev"})
    assert reviewer_doc is not None
    await _assign_reviewer_portfolio(
        fake_db,
        reviewer_user_id=str(reviewer_doc["_id"]),
        investigator_user_id=author_user_id,
    )

    login_reviewer = await api_client.post(
        "/auth/login",
        json={
            "email": "reviewer@luneta.dev",
            "password": "Password123!",
        },
    )
    assert login_reviewer.status_code == 200
    reviewer_token = login_reviewer.json()["access_token"]
    reviewer_headers = {"Authorization": f"Bearer {reviewer_token}"}

    queue = await api_client.get("/workflow/review-queue", headers=reviewer_headers)
    assert queue.status_code == 200
    q_items = queue.json()["items"]
    if not _use_real_mongo():
        assert len(q_items) == 1
    q0 = _queue_row_for_scenario(q_items, scenario_id)
    assert q0["has_prior_approval"] is False
    assert q0["live_public_path"] is None

    start_review = await api_client.post(
        f"/workflow/scenarios/{scenario_id}/start-review",
        headers=reviewer_headers,
    )
    assert start_review.status_code == 200
    assert start_review.json()["state"] == "in_review"

    publish = await api_client.post(
        f"/workflow/scenarios/{scenario_id}/publish",
        headers=reviewer_headers,
    )
    assert publish.status_code == 200
    assert publish.json()["state"] == "published"

    catalog_after_first_publish = await api_client.get("/public/scenarios")
    assert catalog_after_first_publish.status_code == 200
    rows0 = catalog_after_first_publish.json()
    if not _use_real_mongo():
        assert rows0["total"] == 1
    row_pub0 = _public_catalog_row_for(rows0, scenario_id=scenario_id)
    stable_public_slug = _slug_from_public_path(row_pub0["public_path"])
    assert row_pub0["title"] == "Escenario E2E"

    patch_published = await api_client.patch(
        f"/scenarios/{scenario_id}",
        json={"title": "Escenario E2E (editado tras publicar)"},
        headers=author_headers,
    )
    assert patch_published.status_code == 200
    assert patch_published.json()["title"] == "Escenario E2E (editado tras publicar)"
    assert patch_published.json()["state"] == "published"

    catalog_while_pending_review = await api_client.get("/public/scenarios")
    assert catalog_while_pending_review.status_code == 200
    row_pub = _public_catalog_row_for(catalog_while_pending_review.json(), scenario_id=scenario_id)
    assert _slug_from_public_path(row_pub["public_path"]) == stable_public_slug
    assert row_pub["title"] == "Escenario E2E"

    public_read_before_submit = await api_client.get(f"/public/scenarios/{stable_public_slug}")
    assert public_read_before_submit.status_code == 200
    assert public_read_before_submit.json()["title"] == "Escenario E2E"

    submit_repub = await api_client.post(
        f"/scenarios/{scenario_id}/submit-review",
        headers=author_headers,
    )
    assert submit_repub.status_code == 200
    assert submit_repub.json()["state"] == "queued"

    queue_again = await api_client.get("/workflow/review-queue", headers=reviewer_headers)
    assert queue_again.status_code == 200
    qa_items = queue_again.json()["items"]
    if not _use_real_mongo():
        assert len(qa_items) == 1
    qa0 = _queue_row_for_scenario(qa_items, scenario_id)
    assert qa0["has_prior_approval"] is True
    assert qa0["title"] == "Escenario E2E (editado tras publicar)"
    assert qa0["live_public_title"] == "Escenario E2E"

    catalog = await api_client.get("/public/scenarios")
    assert catalog.status_code == 200
    cat_rows = _public_catalog_items(catalog.json())
    ids = [row["id"] for row in cat_rows]
    assert scenario_id in ids
    assert _public_catalog_row_for(cat_rows, scenario_id=scenario_id)["title"] == "Escenario E2E"

    public_read = await api_client.get(f"/public/scenarios/{stable_public_slug}")
    assert public_read.status_code == 200
    assert public_read.json()["id"] == scenario_id
    assert public_read.json()["title"] == "Escenario E2E"

    start_review2 = await api_client.post(
        f"/workflow/scenarios/{scenario_id}/start-review",
        headers=reviewer_headers,
    )
    assert start_review2.status_code == 200

    publish2 = await api_client.post(
        f"/workflow/scenarios/{scenario_id}/publish",
        headers=reviewer_headers,
    )
    assert publish2.status_code == 200

    catalog_final = await api_client.get("/public/scenarios")
    assert catalog_final.status_code == 200
    final_slug = _slug_from_public_path(
        _public_catalog_row_for(catalog_final.json(), scenario_id=scenario_id)["public_path"]
    )
    public_read_after = await api_client.get(f"/public/scenarios/{final_slug}")
    assert public_read_after.status_code == 200
    assert public_read_after.json()["title"] == "Escenario E2E (editado tras publicar)"

    change_pw = await api_client.post(
        "/auth/me/change-password",
        json={"current_password": "Password123!", "new_password": "Newpass456!"},
        headers=author_headers,
    )
    assert change_pw.status_code == 204

    login_after_pw_change = await api_client.post(
        "/auth/login",
        json={"email": "author@luneta.dev", "password": "Newpass456!"},
    )
    assert login_after_pw_change.status_code == 200





