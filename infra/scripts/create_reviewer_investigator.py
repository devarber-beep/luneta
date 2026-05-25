"""Bootstrap a reviewer and an investigator for local development.

Creates verified, active accounts with a fixed password (same style as create_admin.py).
Optionally links the investigator to the reviewer's portfolio.

Usage (from repo root, with venv active):

    python infra/scripts/create_reviewer_investigator.py

Defaults:
  reviewer:     reviewer@luneta.dev / Reviewer123! / nickname reviewer
  investigator: investigator@luneta.dev / Investigator123! / nickname investigator

Override with CLI flags or env vars (LUNETA_BOOTSTRAP_REVIEWER_* / LUNETA_BOOTSTRAP_INVESTIGATOR_*).
Use --no-assign to skip portfolio assignment.
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO / "apps" / "api") not in sys.path:
    sys.path.insert(0, str(REPO / "apps" / "api"))


def _mongodb_uri() -> str:
    env_file = REPO / ".env"
    default = "mongodb://localhost:27017/luneta"
    if not env_file.is_file():
        return os.environ.get("MONGODB_URI", default)
    for line in env_file.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("MONGODB_URI="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return os.environ.get("MONGODB_URI", default)


async def _ensure_bootstrap_user(
    users,
    *,
    email: str,
    password_hash: str,
    nickname: str,
    role,
) -> tuple[object, bool]:
    """Return (user, created) where created is False if the account already existed with that role."""
    existing = await users.get_by_email(email)
    if existing is not None:
        if existing.role == role:
            return existing, False
        msg = f"Error: email {email} is already registered with role {existing.role}"
        raise RuntimeError(msg)
    user = await users.create_bootstrap_account(
        email=email,
        password_hash=password_hash,
        nickname=nickname,
        role=role,
    )
    return user, True


async def _run(
    *,
    reviewer_email: str,
    reviewer_password: str,
    reviewer_nickname: str,
    investigator_email: str,
    investigator_password: str,
    investigator_nickname: str,
    assign: bool,
) -> int:
    from motor.motor_asyncio import AsyncIOMotorClient

    from app.core.security import hash_password
    from app.domain.enums import UserRole
    from app.repositories.audit_events import AuditEventsRepository
    from app.repositories.reviewer_assignments import ReviewerAssignmentsRepository
    from app.repositories.users import UsersRepository

    client = AsyncIOMotorClient(_mongodb_uri())
    db = client.get_default_database()
    users = UsersRepository(db)
    assignments = ReviewerAssignmentsRepository(db)
    await users.ensure_indexes()
    await AuditEventsRepository(db).ensure_indexes()
    await assignments.ensure_indexes()

    reviewer, reviewer_created = await _ensure_bootstrap_user(
        users,
        email=reviewer_email,
        password_hash=hash_password(reviewer_password),
        nickname=reviewer_nickname,
        role=UserRole.REVIEWER,
    )
    investigator, investigator_created = await _ensure_bootstrap_user(
        users,
        email=investigator_email,
        password_hash=hash_password(investigator_password),
        nickname=investigator_nickname,
        role=UserRole.INVESTIGATOR,
    )

    if reviewer_created:
        print(
            f"Created reviewer id={reviewer.id} email={reviewer.email_normalized} nickname={reviewer.nickname}"
        )
    else:
        print(f"Reviewer already exists: {reviewer.email_normalized} (id={reviewer.id})")

    if investigator_created:
        print(
            f"Created investigator id={investigator.id} email={investigator.email_normalized} "
            f"nickname={investigator.nickname}"
        )
    else:
        print(f"Investigator already exists: {investigator.email_normalized} (id={investigator.id})")

    if assign:
        assignment = await assignments.assign(
            reviewer_user_id=reviewer.id or "",
            investigator_user_id=investigator.id or "",
        )
        print(
            f"Portfolio: reviewer {reviewer.email_normalized} -> investigator {investigator.email_normalized} "
            f"(assignment id={assignment.id})"
        )
    else:
        print("Portfolio assignment skipped (--no-assign).")

    print("\nSign-in credentials (email verified, no forced password change):")
    print(f"  Reviewer:     {reviewer_email} / {reviewer_password}")
    print(f"  Investigator: {investigator_email} / {investigator_password}")

    client.close()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Bootstrap reviewer and investigator users for Luneta (dev/local)."
    )
    parser.add_argument(
        "--reviewer-email",
        default=os.environ.get("LUNETA_BOOTSTRAP_REVIEWER_EMAIL", "reviewer@luneta.dev"),
    )
    parser.add_argument(
        "--reviewer-password",
        default=os.environ.get("LUNETA_BOOTSTRAP_REVIEWER_PASSWORD", "Reviewer123!"),
    )
    parser.add_argument(
        "--reviewer-nickname",
        default=os.environ.get("LUNETA_BOOTSTRAP_REVIEWER_NICKNAME", "reviewer"),
    )
    parser.add_argument(
        "--investigator-email",
        default=os.environ.get("LUNETA_BOOTSTRAP_INVESTIGATOR_EMAIL", "investigator@luneta.dev"),
    )
    parser.add_argument(
        "--investigator-password",
        default=os.environ.get("LUNETA_BOOTSTRAP_INVESTIGATOR_PASSWORD", "Investigator123!"),
    )
    parser.add_argument(
        "--investigator-nickname",
        default=os.environ.get("LUNETA_BOOTSTRAP_INVESTIGATOR_NICKNAME", "investigator"),
    )
    parser.add_argument(
        "--no-assign",
        action="store_true",
        help="Do not assign the investigator to the reviewer's portfolio.",
    )
    args = parser.parse_args()
    for label, pwd in (
        ("reviewer password", args.reviewer_password),
        ("investigator password", args.investigator_password),
    ):
        if len(pwd) < 8:
            print(f"Error: {label} must be at least 8 characters", file=sys.stderr)
            return 1
    try:
        return asyncio.run(
            _run(
                reviewer_email=args.reviewer_email,
                reviewer_password=args.reviewer_password,
                reviewer_nickname=args.reviewer_nickname,
                investigator_email=args.investigator_email,
                investigator_password=args.investigator_password,
                investigator_nickname=args.investigator_nickname,
                assign=not args.no_assign,
            )
        )
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
