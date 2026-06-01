"""In-app notifications for the authenticated user."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db import get_db
from app.deps.authz import require_active_user_with_permission
from app.domain.authz_permissions import Permission
from app.models.notification import NotificationModel
from app.models.user import UserModel
from app.repositories.notifications import NotificationsRepository
from app.schemas.notifications import NotificationItem, NotificationListResponse, UnreadCountResponse

router = APIRouter()


def _to_item(row: NotificationModel) -> NotificationItem:
    return NotificationItem(
        id=row.id or "",
        notification_type=row.notification_type.value,
        title=row.title,
        message=row.message,
        entity_type=row.entity_type.value,
        entity_id=row.entity_id,
        scenario_id=row.scenario_id,
        actor_user_id=row.actor_user_id,
        link_path=row.link_path,
        payload=row.payload,
        read_at=row.read_at,
        created_at=row.created_at,
    )


@router.get("", response_model=NotificationListResponse)
async def list_my_notifications(
    unread_only: bool = Query(default=False),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=30, ge=1, le=100),
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: UserModel = Depends(
        require_active_user_with_permission(Permission.NOTIFICATION_READ_SELF)
    ),
) -> NotificationListResponse:
    repo = NotificationsRepository(db)
    user_id = current_user.id or ""
    items, total = await repo.list_for_recipient(
        recipient_user_id=user_id,
        unread_only=unread_only,
        page=page,
        page_size=page_size,
    )
    unread_count = await repo.count_unread(recipient_user_id=user_id)
    return NotificationListResponse(
        items=[_to_item(row) for row in items],
        total=total,
        page=page,
        page_size=page_size,
        unread_count=unread_count,
    )


@router.get("/unread-count", response_model=UnreadCountResponse)
async def unread_count(
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: UserModel = Depends(
        require_active_user_with_permission(Permission.NOTIFICATION_READ_SELF)
    ),
) -> UnreadCountResponse:
    count = await NotificationsRepository(db).count_unread(
        recipient_user_id=current_user.id or ""
    )
    return UnreadCountResponse(unread_count=count)


@router.post("/{notification_id}/read", response_model=NotificationItem)
async def mark_notification_read(
    notification_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: UserModel = Depends(
        require_active_user_with_permission(Permission.NOTIFICATION_UPDATE_SELF)
    ),
) -> NotificationItem:
    from fastapi import HTTPException, status

    repo = NotificationsRepository(db)
    updated = await repo.mark_read(
        notification_id=notification_id,
        recipient_user_id=current_user.id or "",
    )
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    return _to_item(updated)


@router.post("/read-all", response_model=UnreadCountResponse)
async def mark_all_notifications_read(
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: UserModel = Depends(
        require_active_user_with_permission(Permission.NOTIFICATION_UPDATE_SELF)
    ),
) -> UnreadCountResponse:
    await NotificationsRepository(db).mark_all_read(recipient_user_id=current_user.id or "")
    return UnreadCountResponse(unread_count=0)
