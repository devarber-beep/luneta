"""Create the first platform admin user (empty database bootstrap).

Usage (from repo root, with venv active):

    python infra/scripts/create_admin.py

Defaults: admin@luneta.dev / Admin123! / nickname admin.
Override with --email, --password, --nickname or LUNETA_BOOTSTRAP_* env vars.

The account is created verified, active, and without mandatory password change.
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


async def _run(*, email: str, password: str, nickname: str) -> int:
    from motor.motor_asyncio import AsyncIOMotorClient

    from app.core.security import hash_password
    from app.repositories.audit_events import AuditEventsRepository
    from app.repositories.reviewer_assignments import ReviewerAssignmentsRepository
    from app.repositories.users import UsersRepository

    client = AsyncIOMotorClient(_mongodb_uri())
    db = client.get_default_database()
    users = UsersRepository(db)
    await users.ensure_indexes()
    await AuditEventsRepository(db).ensure_indexes()
    await ReviewerAssignmentsRepository(db).ensure_indexes()

    existing = await users.get_by_email(email)
    if existing is not None:
        if existing.role.value == "admin":
            print(f"Admin already exists for {email} (id={existing.id})")
            client.close()
            return 0
        print(f"Error: email {email} is already registered with role {existing.role}", file=sys.stderr)
        client.close()
        return 1

    user = await users.create_admin_account(
        email=email,
        password_hash=hash_password(password),
        nickname=nickname,
    )
    print(f"Created admin user id={user.id} email_normalized={user.email_normalized}")
    client.close()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Bootstrap the first Luneta admin user.")
    parser.add_argument(
        "--email",
        default=os.environ.get("LUNETA_BOOTSTRAP_ADMIN_EMAIL", "admin@luneta.dev"),
    )
    parser.add_argument(
        "--password",
        default=os.environ.get("LUNETA_BOOTSTRAP_ADMIN_PASSWORD", "Admin123!"),
    )
    parser.add_argument("--nickname", default=os.environ.get("LUNETA_BOOTSTRAP_ADMIN_NICKNAME", "admin"))
    args = parser.parse_args()
    if len(args.password) < 8:
        print("Error: password must be at least 8 characters", file=sys.stderr)
        return 1
    return asyncio.run(_run(email=args.email, password=args.password, nickname=args.nickname))


if __name__ == "__main__":
    raise SystemExit(main())
