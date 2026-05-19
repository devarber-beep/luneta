# API tests layout

Tests are grouped by **how** they exercise the system, not by product milestone.

## `capability/` (domain & services, no HTTP)

Pure rules and orchestration: permissions, transitions, service flows with in-memory fakes.

| File | Focus |
|------|--------|
| `test_vertical_slice_domain.py` | Workflow transitions, edit/submit/publish rules, public visibility, collaborators |
| `test_vertical_slice_happy_path_unit.py` | End-to-end happy path via `ScenarioService` + fake repos |
| `test_milestone3_authz.py` | RBAC matrix, portfolio publish/read/reject, contextual `can_*` helpers |

## `http/` (FastAPI routes & JSON contract)

Uses `api_client` (+ `fake_db` by default). Exercises status codes, auth headers, request/response shapes.

| File | Focus |
|------|--------|
| `test_health.py` | `GET /health` |
| `test_vertical_slice_http_e2e.py` | Full vertical slice over HTTP (may need MinIO when uploading assets) |
| `test_auth_session.py` | Login, password gate, profile, avatar, disabled account |
| `test_admin_rf1.py` | Admin user lifecycle (create investigator, roles, deactivate) |
| `test_admin_phase1.py` | Admin profile read/patch, reviewer assignments, audit hook |
| `test_admin_catalogs.py` | Admin classification & ethical-risk catalogs |
| `test_audit_events.py` | Audit log on admin actions |
| `test_dev_last_email_verification.py` | Signup role + dev verification helper |
| `test_orgs.py` | Organizations list |
| `test_milestone3_reviewer_self_publish.py` | `POST .../publish` returns 403 for self-review |

## Shared fixtures

- `../conftest.py` — `fake_db`, `api_client`, optional real Mongo (`LUNETA_TEST_REAL_DB=1`)
- `../user_doc_helpers.py` — helpers for inserting user documents in HTTP tests

Run all tests from `apps/api`:

```bash
pytest
pytest tests/capability
pytest tests/http
```
