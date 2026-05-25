"""Bootstrap one investigator account for local development.

Usage (from repo root, with venv active):

    python infra/scripts/create_investigator.py

Defaults: investigator2@luneta.dev / Investigator2123! / nickname investigator2

Optional: assign to a reviewer's portfolio (--reviewer-email reviewer@luneta.dev).
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


async def _run(
    *,
    email: str,
    password: str,
    nickname: str,
    reviewer_email: str | None,
) -> int:
    from motor.motor_asyncio import AsyncIOMotorClient

    from app.core.security import hash_password
    from app.domain.enums import UserRole
    from app.repositories.reviewer_assignments import ReviewerAssignmentsRepository
    from app.repositories.users import UsersRepository

    client = AsyncIOMotorClient(_mongodb_uri())
    db = client.get_default_database()
    users = UsersRepository(db)
    assignments = ReviewerAssignmentsRepository(db)
    await users.ensure_indexes()
    await assignments.ensure_indexes()

    existing = await users.get_by_email(email)
    if existing is not None:
        if existing.role != UserRole.INVESTIGATOR:
            print(f"Error: email {email} is already registered with role {existing.role}", file=sys.stderr)
            client.close()
            return 1
        investigator = existing
        created = False
        print(f"Investigator already exists: {investigator.email_normalized} (id={investigator.id})")
    else:
        investigator = await users.create_bootstrap_account(
            email=email,
            password_hash=hash_password(password),
            nickname=nickname,
            role=UserRole.INVESTIGATOR,
        )
        created = True
        print(
            f"Created investigator id={investigator.id} email={investigator.email_normalized} "
            f"nickname={investigator.nickname}"
        )

    if reviewer_email:
        reviewer = await users.get_by_email(reviewer_email)
        if reviewer is None:
            print(f"Error: reviewer not found for {reviewer_email}", file=sys.stderr)
            client.close()
            return 1
        if reviewer.role not in {UserRole.REVIEWER, UserRole.ADMIN}:
            print(f"Error: {reviewer_email} is not a reviewer or admin", file=sys.stderr)
            client.close()
            return 1
        assignment = await assignments.assign(
            reviewer_user_id=reviewer.id or "",
            investigator_user_id=investigator.id or "",
        )
        print(
            f"Portfolio: {reviewer.email_normalized} -> {investigator.email_normalized} "
            f"(assignment id={assignment.id})"
        )

    if created:
        print("\nSign-in (verified, no forced password change):")
        print(f"  {email} / {password}")

    client.close()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Bootstrap one Luneta investigator user.")
    parser.add_argument(
        "--email",
        default=os.environ.get("LUNETA_BOOTSTRAP_INVESTIGATOR_EMAIL", "investigator2@luneta.dev"),
    )
    parser.add_argument(
        "--password",
        default=os.environ.get("LUNETA_BOOTSTRAP_INVESTIGATOR_PASSWORD", "Investigator2123!"),
    )
    parser.add_argument(
        "--nickname",
        default=os.environ.get("LUNETA_BOOTSTRAP_INVESTIGATOR_NICKNAME", "investigator2"),
    )
    parser.add_argument(
        "--reviewer-email",
        default=os.environ.get("LUNETA_BOOTSTRAP_ASSIGN_REVIEWER_EMAIL", "reviewer@luneta.dev"),
        help="Assign this investigator to the reviewer's portfolio (omit with --no-assign).",
    )
    parser.add_argument(
        "--no-assign",
        action="store_true",
        help="Do not assign to any reviewer portfolio.",
    )
    args = parser.parse_args()
    if len(args.password) < 8:
        print("Error: password must be at least 8 characters", file=sys.stderr)
        return 1
    return asyncio.run(
        _run(
            email=args.email,
            password=args.password,
            nickname=args.nickname,
            reviewer_email=None if args.no_assign else args.reviewer_email,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
