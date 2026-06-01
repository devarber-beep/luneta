"""Shared wiring for NotificationService in route modules."""
from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.repositories.notifications import NotificationsRepository
from app.repositories.users import UsersRepository
from app.services.mailer_service import MailerService, NoopMailer
from app.services.notification_service import NotificationService


def build_notification_service(
    db: AsyncIOMotorDatabase,
    *,
    mailer: MailerService | NoopMailer | None = None,
) -> NotificationService:
    return NotificationService(
        notifications_repo=NotificationsRepository(db),
        users_repo=UsersRepository(db),
        mailer=mailer,
    )
