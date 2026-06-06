"""HTTP tests for change suggestions."""
from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from bson import ObjectId


async def _signup_and_promote(api_client, fake_db, *, email: str, role: str, token: str) -> dict:
    with patch("app.services.email_verification_service.secrets.token_urlsafe", return_value=token):
        await api_client.post(
            "/auth/signup",
            json={"email": email, "password": "Password123!", "first_name": email.split("@")[0].capitalize(), "last_name": "User"},
        )
        await api_client.post("/auth/verify-email", json={"token": token})
    await fake_db["users"].update_one({"email_normalized": email}, {"$set": {"role": role}})
    login = await api_client.post("/auth/login", json={"email": email, "password": "Password123!"})
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


@pytest.mark.asyncio
async def test_reviewer_suggestion_blocks_publish_until_resolved(api_client, fake_db) -> None:
    owner_h = await _signup_and_promote(
        api_client, fake_db, email="sugowner@luneta.dev", role="investigator", token="sug-owner-tok"
    )
    rev_h = await _signup_and_promote(
        api_client, fake_db, email="sugrev@luneta.dev", role="reviewer", token="sug-rev-tok"
    )
    owner_doc = await fake_db["users"].find_one({"email_normalized": "sugowner@luneta.dev"})
    rev_doc = await fake_db["users"].find_one({"email_normalized": "sugrev@luneta.dev"})
    owner_id = str(owner_doc["_id"])
    rev_id = str(rev_doc["_id"])
    now = datetime.now(UTC)
    await fake_db["reviewer_assignments"].insert_one(
        {
            "reviewer_user_id": rev_id,
            "investigator_user_id": owner_id,
            "created_at": now,
            "created_by_user_id": rev_id,
        }
    )
    create = await api_client.post(
        "/scenarios",
        json={"title": "Suggest me", "description": "Line one.\n\nLine two."},
        headers=owner_h,
    )
    assert create.status_code == 200
    sid = create.json()["id"]
    cat = await fake_db["scenario_classification_catalog"].insert_one(
        {
            "slug": "sug-cat",
            "label": "Cat",
            "is_active": True,
            "sort_order": 0,
            "created_at": now,
            "updated_at": now,
        }
    )
    risk = await fake_db["ethical_risk_catalog"].insert_one(
        {
            "slug": "sug-risk",
            "label": "Risk",
            "is_active": True,
            "sort_order": 0,
            "created_at": now,
            "updated_at": now,
        }
    )
    await fake_db["scenarios"].update_one(
        {"_id": ObjectId(sid)},
        {
            "$set": {
                "cover_image": {
                    "asset_id": "cover-1",
                    "storage_key": f"scenarios/{sid}/cover/cover-1",
                    "mime_type": "image/png",
                    "order": 0,
                }
            }
        },
    )
    await api_client.patch(
        f"/scenarios/{sid}",
        json={
            "category_ids": [str(cat.inserted_id)],
            "ethical_risk_ids": [str(risk.inserted_id)],
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
        headers=owner_h,
    )
    await api_client.post(f"/scenarios/{sid}/submit-review", headers=owner_h)
    await api_client.post(f"/workflow/scenarios/{sid}/start-review", headers=rev_h)
    sug = await api_client.post(
        f"/scenarios/{sid}/suggestions",
        headers=rev_h,
        json={
            "scope": "paragraph",
            "kind": "comment",
            "paragraph_index": 0,
            "body": "Please clarify the opening.",
        },
    )
    assert sug.status_code == 201
    after_sug = await api_client.get(f"/scenarios/{sid}", headers=owner_h)
    assert after_sug.json()["state"] == "in_review"
    blocked = await api_client.post(f"/workflow/scenarios/{sid}/publish", headers=rev_h)
    assert blocked.status_code in (403, 409)


@pytest.mark.asyncio
async def test_reviewer_accept_moves_to_applying_changes(api_client, fake_db) -> None:
    owner_h = await _signup_and_promote(
        api_client, fake_db, email="sugown9@luneta.dev", role="investigator", token="sug-own9-tok"
    )
    rev_h = await _signup_and_promote(
        api_client, fake_db, email="sugrev9@luneta.dev", role="reviewer", token="sug-rev9-tok"
    )
    create = await api_client.post(
        "/scenarios",
        json={"title": "Review cycle", "description": "Para.\n\nTwo."},
        headers=owner_h,
    )
    sid = create.json()["id"]
    now = datetime.now(UTC)
    owner_doc = await fake_db["users"].find_one({"email_normalized": "sugown9@luneta.dev"})
    rev_doc = await fake_db["users"].find_one({"email_normalized": "sugrev9@luneta.dev"})
    await fake_db["reviewer_assignments"].insert_one(
        {
            "reviewer_user_id": str(rev_doc["_id"]),
            "investigator_user_id": str(owner_doc["_id"]),
            "created_at": now,
        }
    )
    cat = await fake_db["scenario_classification_catalog"].insert_one(
        {"slug": "sug9-cat", "label": "Cat", "is_active": True, "sort_order": 0, "created_at": now, "updated_at": now}
    )
    risk = await fake_db["ethical_risk_catalog"].insert_one(
        {"slug": "sug9-risk", "label": "Risk", "is_active": True, "sort_order": 0, "created_at": now, "updated_at": now}
    )
    await fake_db["scenarios"].update_one(
        {"_id": ObjectId(sid)},
        {"$set": {"cover_image": {"asset_id": "c1", "storage_key": f"s/{sid}/c1", "mime_type": "image/png", "order": 0}}},
    )
    await api_client.patch(
        f"/scenarios/{sid}",
        json={
            "category_ids": [str(cat.inserted_id)],
            "ethical_risk_ids": [str(risk.inserted_id)],
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
        headers=owner_h,
    )
    await api_client.post(f"/scenarios/{sid}/submit-review", headers=owner_h)
    await api_client.post(f"/workflow/scenarios/{sid}/start-review", headers=rev_h)
    sug = await api_client.post(
        f"/scenarios/{sid}/suggestions",
        headers=rev_h,
        json={"scope": "paragraph", "kind": "comment", "paragraph_index": 0, "body": "Fix intro"},
    )
    assert sug.status_code == 201
    assert (await api_client.get(f"/scenarios/{sid}", headers=owner_h)).json()["state"] == "in_review"
    req = await api_client.post(
        f"/workflow/scenarios/{sid}/request-changes",
        headers=rev_h,
        json={"note": "Please address the reviewer's suggestions on this scenario."},
    )
    assert req.status_code == 200
    assert (await api_client.get(f"/scenarios/{sid}", headers=owner_h)).json()["state"] == "changes_required"
    accept = await api_client.post(
        f"/scenarios/{sid}/suggestions/{sug.json()['id']}/accept",
        headers=owner_h,
    )
    assert accept.status_code == 200
    assert accept.json()["scenario"]["state"] == "applying_changes"


@pytest.mark.asyncio
async def test_investigator_alternative_text_accept_adds_collaborator(api_client, fake_db) -> None:
    owner_h = await _signup_and_promote(
        api_client, fake_db, email="sugown2@luneta.dev", role="investigator", token="sug-own2-tok"
    )
    collab_h = await _signup_and_promote(
        api_client, fake_db, email="sugcollab@luneta.dev", role="investigator", token="sug-col-tok"
    )
    admin_h = await _signup_and_promote(
        api_client, fake_db, email="sugadmin@luneta.dev", role="admin", token="sug-adm-tok"
    )
    create = await api_client.post(
        "/scenarios",
        json={"title": "Published", "description": "Original.\n\nKeep."},
        headers=owner_h,
    )
    sid = create.json()["id"]
    now = datetime.now(UTC)
    cat = await fake_db["scenario_classification_catalog"].insert_one(
        {
            "slug": "sug2-cat",
            "label": "Cat",
            "is_active": True,
            "sort_order": 0,
            "created_at": now,
            "updated_at": now,
        }
    )
    risk = await fake_db["ethical_risk_catalog"].insert_one(
        {
            "slug": "sug2-risk",
            "label": "Risk",
            "is_active": True,
            "sort_order": 0,
            "created_at": now,
            "updated_at": now,
        }
    )
    await fake_db["scenarios"].update_one(
        {"_id": ObjectId(sid)},
        {
            "$set": {
                "cover_image": {
                    "asset_id": "cover-1",
                    "storage_key": f"scenarios/{sid}/cover/cover-1",
                    "mime_type": "image/png",
                    "order": 0,
                }
            }
        },
    )
    await api_client.patch(
        f"/scenarios/{sid}",
        json={
            "category_ids": [str(cat.inserted_id)],
            "ethical_risk_ids": [str(risk.inserted_id)],
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
        headers=owner_h,
    )
    await api_client.post(f"/scenarios/{sid}/submit-review", headers=owner_h)
    await api_client.post(f"/workflow/scenarios/{sid}/start-review", headers=admin_h)
    await api_client.post(f"/workflow/scenarios/{sid}/publish", headers=admin_h)
    sug = await api_client.post(
        f"/scenarios/{sid}/suggestions",
        headers=collab_h,
        json={
            "scope": "paragraph",
            "kind": "alternative_text",
            "paragraph_index": 0,
            "body": "Revised opening.",
        },
    )
    assert sug.status_code == 201
    accept = await api_client.post(
        f"/scenarios/{sid}/suggestions/{sug.json()['id']}/accept",
        headers=owner_h,
    )
    assert accept.status_code == 200
    scenario = accept.json()["scenario"]
    assert scenario["state"] == "draft"
    assert "Revised opening." not in scenario["description"]
    apply = await api_client.post(
        f"/scenarios/{sid}/suggestions/{sug.json()['id']}/apply-text",
        headers=owner_h,
    )
    assert apply.status_code == 200
    assert "Revised opening." in apply.json()["scenario"]["description"]
    collab_ids = [c["user_id"] for c in scenario["collaborators"]]
    collab_doc = await fake_db["users"].find_one({"email_normalized": "sugcollab@luneta.dev"})
    assert str(collab_doc["_id"]) in collab_ids


@pytest.mark.asyncio
async def test_suggester_cannot_list_suggestions(api_client, fake_db) -> None:
    owner_h = await _signup_and_promote(
        api_client, fake_db, email="sugown3@luneta.dev", role="investigator", token="sug-own3-tok"
    )
    rev_h = await _signup_and_promote(
        api_client, fake_db, email="sugrev3@luneta.dev", role="reviewer", token="sug-rev3-tok"
    )
    create = await api_client.post(
        "/scenarios",
        json={"title": "Hidden suggestions", "description": "Para one.\n\nPara two."},
        headers=owner_h,
    )
    sid = create.json()["id"]
    now = datetime.now(UTC)
    cat = await fake_db["scenario_classification_catalog"].insert_one(
        {
            "slug": "sug3-cat",
            "label": "Cat",
            "is_active": True,
            "sort_order": 0,
            "created_at": now,
            "updated_at": now,
        }
    )
    risk = await fake_db["ethical_risk_catalog"].insert_one(
        {
            "slug": "sug3-risk",
            "label": "Risk",
            "is_active": True,
            "sort_order": 0,
            "created_at": now,
            "updated_at": now,
        }
    )
    await fake_db["scenarios"].update_one(
        {"_id": ObjectId(sid)},
        {
            "$set": {
                "cover_image": {
                    "asset_id": "cover-1",
                    "storage_key": f"scenarios/{sid}/cover/cover-1",
                    "mime_type": "image/png",
                    "order": 0,
                }
            }
        },
    )
    await api_client.patch(
        f"/scenarios/{sid}",
        json={
            "category_ids": [str(cat.inserted_id)],
            "ethical_risk_ids": [str(risk.inserted_id)],
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
        headers=owner_h,
    )
    owner_doc = await fake_db["users"].find_one({"email_normalized": "sugown3@luneta.dev"})
    rev_doc = await fake_db["users"].find_one({"email_normalized": "sugrev3@luneta.dev"})
    await fake_db["reviewer_assignments"].insert_one(
        {
            "reviewer_user_id": str(rev_doc["_id"]),
            "investigator_user_id": str(owner_doc["_id"]),
            "created_at": now,
        }
    )
    sub = await api_client.post(f"/scenarios/{sid}/submit-review", headers=owner_h)
    assert sub.status_code == 200
    await api_client.post(f"/workflow/scenarios/{sid}/start-review", headers=rev_h)
    sug = await api_client.post(
        f"/scenarios/{sid}/suggestions",
        headers=rev_h,
        json={
            "scope": "paragraph",
            "kind": "comment",
            "paragraph_index": 0,
            "body": "Private note",
        },
    )
    assert sug.status_code == 201


@pytest.mark.asyncio
async def test_suggester_can_list_own_suggestions(api_client, fake_db) -> None:
    owner_h = await _signup_and_promote(
        api_client, fake_db, email="sugown6@luneta.dev", role="investigator", token="sug-own6-tok"
    )
    collab_h = await _signup_and_promote(
        api_client, fake_db, email="sugcol6@luneta.dev", role="investigator", token="sug-col6-tok"
    )
    admin_h = await _signup_and_promote(
        api_client, fake_db, email="sugadm6@luneta.dev", role="admin", token="sug-adm6-tok"
    )
    create = await api_client.post(
        "/scenarios",
        json={"title": "Peer", "description": "Para.\n\nTwo."},
        headers=owner_h,
    )
    sid = create.json()["id"]
    now = datetime.now(UTC)
    cat = await fake_db["scenario_classification_catalog"].insert_one(
        {"slug": "sug6-cat", "label": "Cat", "is_active": True, "sort_order": 0, "created_at": now, "updated_at": now}
    )
    risk = await fake_db["ethical_risk_catalog"].insert_one(
        {"slug": "sug6-risk", "label": "Risk", "is_active": True, "sort_order": 0, "created_at": now, "updated_at": now}
    )
    await fake_db["scenarios"].update_one(
        {"_id": ObjectId(sid)},
        {"$set": {"cover_image": {"asset_id": "c1", "storage_key": f"s/{sid}/c1", "mime_type": "image/png", "order": 0}}},
    )
    await api_client.patch(
        f"/scenarios/{sid}",
        json={
            "category_ids": [str(cat.inserted_id)],
            "ethical_risk_ids": [str(risk.inserted_id)],
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
        headers=owner_h,
    )
    await api_client.post(f"/scenarios/{sid}/submit-review", headers=owner_h)
    await api_client.post(f"/workflow/scenarios/{sid}/start-review", headers=admin_h)
    await api_client.post(f"/workflow/scenarios/{sid}/publish", headers=admin_h)
    before = await api_client.get(f"/scenarios/{sid}/suggestions", headers=collab_h)
    assert before.status_code == 403
    sug = await api_client.post(
        f"/scenarios/{sid}/suggestions",
        headers=collab_h,
        json={
            "scope": "paragraph",
            "kind": "alternative_text",
            "paragraph_index": 0,
            "body": "Better intro",
        },
    )
    assert sug.status_code == 201


@pytest.mark.asyncio
async def test_reviewer_review_feedback_status(api_client, fake_db) -> None:
    owner_h = await _signup_and_promote(
        api_client, fake_db, email="sugown4@luneta.dev", role="investigator", token="sug-own4-tok"
    )
    rev_h = await _signup_and_promote(
        api_client, fake_db, email="sugrev4@luneta.dev", role="reviewer", token="sug-rev4-tok"
    )
    create = await api_client.post(
        "/scenarios",
        json={"title": "Feedback status", "description": "One.\n\nTwo."},
        headers=owner_h,
    )
    sid = create.json()["id"]
    now = datetime.now(UTC)
    cat = await fake_db["scenario_classification_catalog"].insert_one(
        {"slug": "sug4-cat", "label": "Cat", "is_active": True, "sort_order": 0, "created_at": now, "updated_at": now}
    )
    risk = await fake_db["ethical_risk_catalog"].insert_one(
        {"slug": "sug4-risk", "label": "Risk", "is_active": True, "sort_order": 0, "created_at": now, "updated_at": now}
    )
    await fake_db["scenarios"].update_one(
        {"_id": ObjectId(sid)},
        {"$set": {"cover_image": {"asset_id": "c1", "storage_key": f"s/{sid}/c1", "mime_type": "image/png", "order": 0}}},
    )
    await api_client.patch(
        f"/scenarios/{sid}",
        json={
            "category_ids": [str(cat.inserted_id)],
            "ethical_risk_ids": [str(risk.inserted_id)],
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
        headers=owner_h,
    )
    owner_doc = await fake_db["users"].find_one({"email_normalized": "sugown4@luneta.dev"})
    rev_doc = await fake_db["users"].find_one({"email_normalized": "sugrev4@luneta.dev"})
    await fake_db["reviewer_assignments"].insert_one(
        {
            "reviewer_user_id": str(rev_doc["_id"]),
            "investigator_user_id": str(owner_doc["_id"]),
            "created_at": now,
        }
    )
    before = await api_client.get(f"/scenarios/{sid}/suggestions/review-feedback", headers=rev_h)
    assert before.status_code == 403
    sub = await api_client.post(f"/scenarios/{sid}/submit-review", headers=owner_h)
    assert sub.status_code == 200
    await api_client.post(f"/workflow/scenarios/{sid}/start-review", headers=rev_h)
    empty = await api_client.get(f"/scenarios/{sid}/suggestions/review-feedback", headers=rev_h)
    assert empty.status_code == 200
    assert empty.json()["has_submitted_feedback"] is False
    await api_client.post(
        f"/scenarios/{sid}/suggestions",
        headers=rev_h,
        json={"scope": "scenario", "kind": "comment", "paragraph_index": None, "body": "Overall feedback"},
    )
    after = await api_client.get(f"/scenarios/{sid}/suggestions/review-feedback", headers=rev_h)
    assert after.status_code == 200
    assert after.json()["has_submitted_feedback"] is True


@pytest.mark.asyncio
async def test_investigator_scenario_comment_on_other_published(api_client, fake_db) -> None:
    owner_h = await _signup_and_promote(
        api_client, fake_db, email="sugown5@luneta.dev", role="investigator", token="sug-own5-tok"
    )
    other_h = await _signup_and_promote(
        api_client, fake_db, email="sugoth5@luneta.dev", role="investigator", token="sug-oth5-tok"
    )
    create = await api_client.post(
        "/scenarios",
        json={"title": "Peer scenario", "description": "Body text."},
        headers=owner_h,
    )
    sid = create.json()["id"]
    now = datetime.now(UTC)
    cat = await fake_db["scenario_classification_catalog"].insert_one(
        {"slug": "sug5-cat", "label": "Cat", "is_active": True, "sort_order": 0, "created_at": now, "updated_at": now}
    )
    risk = await fake_db["ethical_risk_catalog"].insert_one(
        {"slug": "sug5-risk", "label": "Risk", "is_active": True, "sort_order": 0, "created_at": now, "updated_at": now}
    )
    await fake_db["scenarios"].update_one(
        {"_id": ObjectId(sid)},
        {"$set": {"cover_image": {"asset_id": "c1", "storage_key": f"s/{sid}/c1", "mime_type": "image/png", "order": 0}}},
    )
    await api_client.patch(
        f"/scenarios/{sid}",
        json={
            "category_ids": [str(cat.inserted_id)],
            "ethical_risk_ids": [str(risk.inserted_id)],
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
        headers=owner_h,
    )
    await api_client.post(f"/scenarios/{sid}/submit-review", headers=owner_h)
    admin_h = await _signup_and_promote(
        api_client, fake_db, email="sugadm5@luneta.dev", role="admin", token="sug-adm5-tok"
    )
    await api_client.post(f"/workflow/scenarios/{sid}/start-review", headers=admin_h)
    await api_client.post(f"/workflow/scenarios/{sid}/publish", headers=admin_h)
    sug = await api_client.post(
        f"/scenarios/{sid}/suggestions",
        headers=other_h,
        json={"scope": "scenario", "kind": "comment", "body": "Consider expanding the ethical section."},
    )
    assert sug.status_code == 201


@pytest.mark.asyncio
async def test_investigator_suggests_on_other_published_scenario(api_client, fake_db) -> None:
    owner_h = await _signup_and_promote(
        api_client, fake_db, email="sugown4@luneta.dev", role="investigator", token="sug-own4-tok"
    )
    other_h = await _signup_and_promote(
        api_client, fake_db, email="sugother@luneta.dev", role="investigator", token="sug-oth-tok"
    )
    create = await api_client.post(
        "/scenarios",
        json={"title": "Published peer", "description": "First para here.\n\nSecond para here."},
        headers=owner_h,
    )
    sid = create.json()["id"]
    now = datetime.now(UTC)
    cat = await fake_db["scenario_classification_catalog"].insert_one(
        {
            "slug": "sug4-cat",
            "label": "Cat",
            "is_active": True,
            "sort_order": 0,
            "created_at": now,
            "updated_at": now,
        }
    )
    risk = await fake_db["ethical_risk_catalog"].insert_one(
        {
            "slug": "sug4-risk",
            "label": "Risk",
            "is_active": True,
            "sort_order": 0,
            "created_at": now,
            "updated_at": now,
        }
    )
    await fake_db["scenarios"].update_one(
        {"_id": ObjectId(sid)},
        {
            "$set": {
                "cover_image": {
                    "asset_id": "cover-1",
                    "storage_key": f"scenarios/{sid}/cover/cover-1",
                    "mime_type": "image/png",
                    "order": 0,
                }
            }
        },
    )
    await api_client.patch(
        f"/scenarios/{sid}",
        json={
            "category_ids": [str(cat.inserted_id)],
            "ethical_risk_ids": [str(risk.inserted_id)],
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
        headers=owner_h,
    )
    await api_client.post(f"/scenarios/{sid}/submit-review", headers=owner_h)
    admin_h = await _signup_and_promote(
        api_client, fake_db, email="sugadm4@luneta.dev", role="admin", token="sug-adm4-tok"
    )
    await api_client.post(f"/workflow/scenarios/{sid}/start-review", headers=admin_h)
    pub = await api_client.post(f"/workflow/scenarios/{sid}/publish", headers=admin_h)
    assert pub.status_code == 200
    slug = (await fake_db["scenarios"].find_one({"_id": ObjectId(sid)}))["public_slug"]
    public = await api_client.get(f"/public/scenarios/{slug}")
    assert public.status_code == 200
    assert public.json()["author_user_id"]
    paras = await api_client.get(f"/scenarios/{sid}/suggestions/paragraphs", headers=other_h)
    assert paras.status_code == 200
    assert len(paras.json()["paragraphs"]) >= 1
    sug = await api_client.post(
        f"/scenarios/{sid}/suggestions",
        headers=other_h,
        json={
            "scope": "paragraph",
            "kind": "alternative_text",
            "paragraph_index": 0,
            "body": "Suggested replacement for paragraph one.",
        },
    )
    assert sug.status_code == 201


@pytest.mark.asyncio
async def test_reviewer_published_suggestion_blocked_if_they_reviewed(api_client, fake_db) -> None:
    owner_h = await _signup_and_promote(
        api_client, fake_db, email="sugown7@luneta.dev", role="investigator", token="sug-own7-tok"
    )
    rev_h = await _signup_and_promote(
        api_client, fake_db, email="sugrev7@luneta.dev", role="reviewer", token="sug-rev7-tok"
    )
    other_rev_h = await _signup_and_promote(
        api_client, fake_db, email="sugrev7b@luneta.dev", role="reviewer", token="sug-rev7b-tok"
    )
    create = await api_client.post(
        "/scenarios",
        json={"title": "Reviewed pub", "description": "Body.\n\nMore."},
        headers=owner_h,
    )
    sid = create.json()["id"]
    now = datetime.now(UTC)
    owner_doc = await fake_db["users"].find_one({"email_normalized": "sugown7@luneta.dev"})
    rev_doc = await fake_db["users"].find_one({"email_normalized": "sugrev7@luneta.dev"})
    await fake_db["reviewer_assignments"].insert_one(
        {
            "reviewer_user_id": str(rev_doc["_id"]),
            "investigator_user_id": str(owner_doc["_id"]),
            "created_at": now,
        }
    )
    cat = await fake_db["scenario_classification_catalog"].insert_one(
        {"slug": "sug7-cat", "label": "Cat", "is_active": True, "sort_order": 0, "created_at": now, "updated_at": now}
    )
    risk = await fake_db["ethical_risk_catalog"].insert_one(
        {"slug": "sug7-risk", "label": "Risk", "is_active": True, "sort_order": 0, "created_at": now, "updated_at": now}
    )
    await fake_db["scenarios"].update_one(
        {"_id": ObjectId(sid)},
        {"$set": {"cover_image": {"asset_id": "c1", "storage_key": f"s/{sid}/c1", "mime_type": "image/png", "order": 0}}},
    )
    await api_client.patch(
        f"/scenarios/{sid}",
        json={
            "category_ids": [str(cat.inserted_id)],
            "ethical_risk_ids": [str(risk.inserted_id)],
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
        headers=owner_h,
    )
    await api_client.post(f"/scenarios/{sid}/submit-review", headers=owner_h)
    await api_client.post(f"/workflow/scenarios/{sid}/start-review", headers=rev_h)
    await api_client.post(f"/workflow/scenarios/{sid}/publish", headers=rev_h)
    blocked = await api_client.post(
        f"/scenarios/{sid}/suggestions",
        headers=rev_h,
        json={"scope": "paragraph", "kind": "comment", "paragraph_index": 0, "body": "Too late"},
    )
    assert blocked.status_code == 403
    get_self = await api_client.get(f"/scenarios/{sid}", headers=rev_h)
    assert get_self.status_code == 200
    assert get_self.json()["can_create_suggestion"] is False
    allowed = await api_client.post(
        f"/scenarios/{sid}/suggestions",
        headers=other_rev_h,
        json={"scope": "scenario", "kind": "comment", "paragraph_index": None, "body": "Fresh eyes"},
    )
    assert allowed.status_code == 201


@pytest.mark.asyncio
async def test_investigator_paragraph_comment_on_published(api_client, fake_db) -> None:
    owner_h = await _signup_and_promote(
        api_client, fake_db, email="sugown8@luneta.dev", role="investigator", token="sug-own8-tok"
    )
    peer_h = await _signup_and_promote(
        api_client, fake_db, email="sugpeer8@luneta.dev", role="investigator", token="sug-peer8-tok"
    )
    admin_h = await _signup_and_promote(
        api_client, fake_db, email="sugadm8@luneta.dev", role="admin", token="sug-adm8-tok"
    )
    create = await api_client.post(
        "/scenarios",
        json={"title": "Comment para", "description": "Block one."},
        headers=owner_h,
    )
    sid = create.json()["id"]
    now = datetime.now(UTC)
    cat = await fake_db["scenario_classification_catalog"].insert_one(
        {"slug": "sug8-cat", "label": "Cat", "is_active": True, "sort_order": 0, "created_at": now, "updated_at": now}
    )
    risk = await fake_db["ethical_risk_catalog"].insert_one(
        {"slug": "sug8-risk", "label": "Risk", "is_active": True, "sort_order": 0, "created_at": now, "updated_at": now}
    )
    await fake_db["scenarios"].update_one(
        {"_id": ObjectId(sid)},
        {"$set": {"cover_image": {"asset_id": "c1", "storage_key": f"s/{sid}/c1", "mime_type": "image/png", "order": 0}}},
    )
    await api_client.patch(
        f"/scenarios/{sid}",
        json={
            "category_ids": [str(cat.inserted_id)],
            "ethical_risk_ids": [str(risk.inserted_id)],
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
        headers=owner_h,
    )
    await api_client.post(f"/scenarios/{sid}/submit-review", headers=owner_h)
    await api_client.post(f"/workflow/scenarios/{sid}/start-review", headers=admin_h)
    await api_client.post(f"/workflow/scenarios/{sid}/publish", headers=admin_h)
    blocked = await api_client.post(
        f"/scenarios/{sid}/suggestions",
        headers=peer_h,
        json={"scope": "paragraph", "kind": "comment", "paragraph_index": 0, "body": "Consider rephrasing"},
    )
    assert blocked.status_code == 400
    allowed = await api_client.post(
        f"/scenarios/{sid}/suggestions",
        headers=peer_h,
        json={
            "scope": "paragraph",
            "kind": "alternative_text",
            "paragraph_index": 0,
            "body": "Revised opening line.",
        },
    )
    assert allowed.status_code == 201


@pytest.mark.asyncio
async def test_suggestion_author_visible_only_to_admin(api_client, fake_db) -> None:
    owner_h = await _signup_and_promote(
        api_client, fake_db, email="suganonown@luneta.dev", role="investigator", token="sug-anon-own"
    )
    rev_h = await _signup_and_promote(
        api_client, fake_db, email="suganonrev@luneta.dev", role="reviewer", token="sug-anon-rev"
    )
    admin_h = await _signup_and_promote(
        api_client, fake_db, email="suganonadm@luneta.dev", role="admin", token="sug-anon-adm"
    )
    owner_doc = await fake_db["users"].find_one({"email_normalized": "suganonown@luneta.dev"})
    rev_doc = await fake_db["users"].find_one({"email_normalized": "suganonrev@luneta.dev"})
    rev_id = str(rev_doc["_id"])
    now = datetime.now(UTC)
    await fake_db["reviewer_assignments"].insert_one(
        {
            "reviewer_user_id": rev_id,
            "investigator_user_id": str(owner_doc["_id"]),
            "created_at": now,
            "created_by_user_id": rev_id,
        }
    )
    create = await api_client.post(
        "/scenarios",
        json={"title": "Anon suggest", "description": "Line one.\n\nLine two."},
        headers=owner_h,
    )
    sid = create.json()["id"]
    cat = await fake_db["scenario_classification_catalog"].insert_one(
        {"slug": "sug-anon-cat", "label": "Cat", "is_active": True, "sort_order": 0, "created_at": now, "updated_at": now}
    )
    risk = await fake_db["ethical_risk_catalog"].insert_one(
        {"slug": "sug-anon-risk", "label": "Risk", "is_active": True, "sort_order": 0, "created_at": now, "updated_at": now}
    )
    await fake_db["scenarios"].update_one(
        {"_id": ObjectId(sid)},
        {"$set": {"cover_image": {"asset_id": "c1", "storage_key": f"s/{sid}/c1", "mime_type": "image/png", "order": 0}}},
    )
    await api_client.patch(
        f"/scenarios/{sid}",
        json={
            "category_ids": [str(cat.inserted_id)],
            "ethical_risk_ids": [str(risk.inserted_id)],
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
        headers=owner_h,
    )
    await api_client.post(f"/scenarios/{sid}/submit-review", headers=owner_h)
    await api_client.post(f"/workflow/scenarios/{sid}/start-review", headers=rev_h)
    await api_client.post(
        f"/scenarios/{sid}/suggestions",
        headers=rev_h,
        json={"scope": "paragraph", "kind": "comment", "paragraph_index": 0, "body": "Anonymous to owner"},
    )
    owner_list = await api_client.get(f"/scenarios/{sid}/suggestions", headers=owner_h)
    assert owner_list.status_code == 200
    assert owner_list.json()["items"][0]["author_user_id"] == ""
    assert owner_list.json()["items"][0]["author_role"] == "reviewer"

    rev_list = await api_client.get(f"/scenarios/{sid}/suggestions", headers=rev_h)
    assert rev_list.status_code == 200
    assert rev_list.json()["items"][0]["author_user_id"] == ""

    admin_list = await api_client.get(f"/scenarios/{sid}/suggestions", headers=admin_h)
    assert admin_list.status_code == 200
    assert admin_list.json()["items"][0]["author_user_id"] == rev_id







