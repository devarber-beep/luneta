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

    create = await api_client.post(
        "/scenarios",
        json={
            "slug": "escenario-e2e",
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
    assert mine.json()[0]["slug"] == "escenario-e2e"

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

    create_comment = await api_client.post(
        f"/scenarios/{scenario_id}/comments",
        json={
            "body_markdown": "Comentario interno",
            "revision_number": 2,
            "section_key": "body",
            "field_path": "body_markdown",
        },
        headers=author_headers,
    )
    assert create_comment.status_code == 200
    assert create_comment.json()["scenario_id"] == scenario_id
    assert create_comment.json()["body_markdown"] == "Comentario interno"

    with patch("app.services.email_verification_service.secrets.token_urlsafe", return_value="reviewer-token"):
        signup_reviewer = await api_client.post(
            "/auth/signup",
            json={
                "email": "reviewer@luneta.dev",
                "password": "Password123!",
                "role": "reviewer",
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

    list_comments = await api_client.get(
        f"/scenarios/{scenario_id}/comments",
        headers=reviewer_headers,
    )
    assert list_comments.status_code == 200
    assert len(list_comments.json()["items"]) == 1

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

    catalog = await api_client.get("/public/scenarios")
    assert catalog.status_code == 200
    slugs = [row["slug"] for row in catalog.json()]
    assert "escenario-e2e" in slugs

    public_read = await api_client.get("/public/scenarios/escenario-e2e")
    assert public_read.status_code == 200
    assert public_read.json()["slug"] == "escenario-e2e"
    assert public_read.json()["id"] == scenario_id

    pub_comments = await api_client.get("/public/scenarios/escenario-e2e/comments")
    assert pub_comments.status_code == 200
    assert pub_comments.json()["slug"] == "escenario-e2e"
    assert len(pub_comments.json()["items"]) >= 1

    pub_post = await api_client.post(
        "/public/scenarios/escenario-e2e/comments",
        json={"body_markdown": "Comentario en publicado"},
        headers=author_headers,
    )
    assert pub_post.status_code == 200
    assert pub_post.json()["body_markdown"] == "Comentario en publicado"

    pub_comments2 = await api_client.get("/public/scenarios/escenario-e2e/comments")
    assert len(pub_comments2.json()["items"]) >= 2
