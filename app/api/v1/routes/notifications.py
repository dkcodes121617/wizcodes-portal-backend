"""Student notification inbox."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_student
from app.db.session import get_session
from app.models.student import Student
from app.schemas.notification import (
    NotificationResponse,
    NotificationUnreadCountResponse,
)
from app.services.notifications import (
    count_unread_for_student,
    list_notifications_for_student,
    mark_all_read_for_student,
    mark_notification_read,
)

router = APIRouter(prefix="/student/notifications", tags=["student-notifications"])


@router.get(
    "",
    response_model=list[NotificationResponse],
    summary="List notifications for the current student",
)
async def list_my_notifications(
    student: Student = Depends(get_current_student),
    session: AsyncSession = Depends(get_session),
) -> list[NotificationResponse]:
    notifications = await list_notifications_for_student(session, student.id)
    return [NotificationResponse.model_validate(row) for row in notifications]


@router.get(
    "/unread-count",
    response_model=NotificationUnreadCountResponse,
    summary="Unread notification count for the current student",
)
async def get_my_unread_count(
    student: Student = Depends(get_current_student),
    session: AsyncSession = Depends(get_session),
) -> NotificationUnreadCountResponse:
    count = await count_unread_for_student(session, student.id)
    return NotificationUnreadCountResponse(unread_count=count)


@router.patch(
    "/read-all",
    summary="Mark all notifications as read",
)
async def mark_all_my_notifications_read(
    student: Student = Depends(get_current_student),
    session: AsyncSession = Depends(get_session),
) -> dict[str, int]:
    updated = await mark_all_read_for_student(session, student.id)
    await session.commit()
    return {"updated": updated}


@router.patch(
    "/{notification_id}/read",
    response_model=NotificationResponse,
    summary="Mark a notification as read",
)
async def mark_my_notification_read(
    notification_id: uuid.UUID,
    student: Student = Depends(get_current_student),
    session: AsyncSession = Depends(get_session),
) -> NotificationResponse:
    notification = await mark_notification_read(session, student.id, notification_id)
    if notification is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )
    await session.commit()
    await session.refresh(notification)
    return NotificationResponse.model_validate(notification)
