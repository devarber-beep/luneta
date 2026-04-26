"""HTTP integration test for the vertical slice happy path."""
from __future__ import annotations

from unittest.mock import patch

import pytest


@pytest.mark.asyncio
async def test_vertical_slice_http_happy_path(api_client):
    verify_token = "test-verify-token"

    with patch("app.services.email_verification_service.secrets.token_urlsafe", return_value=verify_token):
        signup_author = await api_client.post(
            "/auth/signup",
            json={
                "email": "author@luneta.dev",
                "password": "Password123!",
                "role": "author",
                "nickname": "author",
            },
        )
        assert signup_author.status_code == 200
        author_user_id = signup_author.json()["user_id"]

        verify_author = await api_client.post("/auth/verify-email", json={"token": verify_token})
        assert verify_author.status_code == 200
        assert verify_author.json()["verified"] is True

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
            "body_markdown": "Contenido inicial",
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
        json={"body_markdown": "Contenido revisado"},
        headers=author_headers,
    )
    assert patch_draft.status_code == 200
    assert patch_draft.json()["current_revision_number"] == 2

    submit = await api_client.post(
        f"/scenarios/{scenario_id}/submit-review",
        headers=author_headers,
    )
    assert submit.status_code == 200
    assert submit.json()["state"] == "in_review"

    with patch("app.services.email_verification_service.secrets.token_urlsafe", return_value="reviewer-token"):
        signup_reviewer = await api_client.post(
            "/auth/signup",
            json={
                "email": "reviewer@luneta.dev",
                "password": "Password123!",
                "role": "reviewer",
                "nickname": "reviewer",
            },
        )
        assert signup_reviewer.status_code == 200

        verify_reviewer = await api_client.post("/auth/verify-email", json={"token": "reviewer-token"})
        assert verify_reviewer.status_code == 200

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
    assert len(queue.json()["items"]) == 1
    assert queue.json()["items"][0]["scenario_id"] == scenario_id
    scenario_slug = queue.json()["items"][0]["slug"]
    assert queue.json()["items"][0]["has_prior_approval"] is False

    approve = await api_client.post(
        f"/workflow/scenarios/{scenario_id}/approve",
        headers=reviewer_headers,
    )
    assert approve.status_code == 200
    assert approve.json()["state"] == "approved"

    publish = await api_client.post(
        f"/workflow/scenarios/{scenario_id}/publish",
        headers=reviewer_headers,
    )
    assert publish.status_code == 200
    assert publish.json()["state"] == "published"

    catalog_after_first_publish = await api_client.get("/public/scenarios")
    assert catalog_after_first_publish.status_code == 200
    rows0 = catalog_after_first_publish.json()
    assert len(rows0) == 1
    stable_public_slug = rows0[0]["slug"]
    assert rows0[0]["title"] == "Escenario E2E"

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
    row_pub = catalog_while_pending_review.json()[0]
    assert row_pub["slug"] == stable_public_slug
    assert row_pub["title"] == "Escenario E2E"

    public_read_before_submit = await api_client.get(f"/public/scenarios/{stable_public_slug}")
    assert public_read_before_submit.status_code == 200
    assert public_read_before_submit.json()["title"] == "Escenario E2E"

    submit_repub = await api_client.post(
        f"/scenarios/{scenario_id}/submit-review",
        headers=author_headers,
    )
    assert submit_repub.status_code == 200
    assert submit_repub.json()["state"] == "in_review"

    queue_again = await api_client.get("/workflow/review-queue", headers=reviewer_headers)
    assert queue_again.status_code == 200
    assert len(queue_again.json()["items"]) == 1
    assert queue_again.json()["items"][0]["has_prior_approval"] is True
    assert queue_again.json()["items"][0]["title"] == "Escenario E2E (editado tras publicar)"
    assert queue_again.json()["items"][0]["live_public_title"] == "Escenario E2E"

    catalog = await api_client.get("/public/scenarios")
    assert catalog.status_code == 200
    ids = [row["id"] for row in catalog.json()]
    assert scenario_id in ids
    assert catalog.json()[0]["title"] == "Escenario E2E"

    public_read = await api_client.get(f"/public/scenarios/{stable_public_slug}")
    assert public_read.status_code == 200
    assert public_read.json()["id"] == scenario_id
    assert public_read.json()["slug"] == stable_public_slug
    assert public_read.json()["title"] == "Escenario E2E"

    approve2 = await api_client.post(
        f"/workflow/scenarios/{scenario_id}/approve",
        headers=reviewer_headers,
    )
    assert approve2.status_code == 200
    publish2 = await api_client.post(
        f"/workflow/scenarios/{scenario_id}/publish",
        headers=reviewer_headers,
    )
    assert publish2.status_code == 200

    catalog_final = await api_client.get("/public/scenarios")
    assert catalog_final.status_code == 200
    final_slug = catalog_final.json()[0]["slug"]
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
