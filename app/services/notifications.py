"""Notification business logic."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification
from app.models.student import Student
from app.schemas.notification import NotificationAudience, NotificationSendRequest


async def list_notifications_for_student(
    session: AsyncSession,
    student_id: uuid.UUID,
    *,
    limit: int = 50,
) -> list[Notification]:
    result = await session.execute(
        select(Notification)
        .where(Notification.student_id == student_id)
        .order_by(Notification.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def count_unread_for_student(session: AsyncSession, student_id: uuid.UUID) -> int:
    result = await session.execute(
        select(func.count())
        .select_from(Notification)
        .where(
            Notification.student_id == student_id,
            Notification.read_at.is_(None),
        )
    )
    return int(result.scalar_one())


async def mark_notification_read(
    session: AsyncSession,
    student_id: uuid.UUID,
    notification_id: uuid.UUID,
) -> Notification | None:
    result = await session.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.student_id == student_id,
        )
    )
    notification = result.scalar_one_or_none()
    if notification is None:
        return None
    if notification.read_at is None:
        notification.read_at = datetime.now(UTC)
    return notification


async def mark_all_read_for_student(session: AsyncSession, student_id: uuid.UUID) -> int:
    result = await session.execute(
        select(Notification).where(
            Notification.student_id == student_id,
            Notification.read_at.is_(None),
        )
    )
    notifications = list(result.scalars().all())
    now = datetime.now(UTC)
    for notification in notifications:
        notification.read_at = now
    return len(notifications)


async def _resolve_recipient_ids(
    session: AsyncSession,
    body: NotificationSendRequest,
) -> list[uuid.UUID]:
    if body.audience == "single":
        assert body.student_id is not None
        result = await session.execute(select(Student.id).where(Student.id == body.student_id))
        if result.scalar_one_or_none() is None:
            return []
        return [body.student_id]

    if body.audience == "custom":
        assert body.student_ids is not None
        unique_ids = list(dict.fromkeys(body.student_ids))
        if not unique_ids:
            return []
        result = await session.execute(select(Student.id).where(Student.id.in_(unique_ids)))
        return list(result.scalars().all())

    query = select(Student.id)
    if body.audience == "pending":
        query = query.where(Student.access_status == "pending")
    elif body.audience == "granted":
        query = query.where(Student.access_status == "granted")

    result = await session.execute(query.order_by(Student.created_at.desc()))
    return list(result.scalars().all())


async def send_notifications(
    session: AsyncSession,
    admin_id: uuid.UUID,
    body: NotificationSendRequest,
) -> tuple[int, list[uuid.UUID]]:
    recipient_ids = await _resolve_recipient_ids(session, body)
    if not recipient_ids:
        return 0, []

    created_ids: list[uuid.UUID] = []
    for student_id in recipient_ids:
        notification = Notification(
            student_id=student_id,
            title=body.title,
            body=body.body,
            sent_by_admin_id=admin_id,
        )
        session.add(notification)
        await session.flush()
        created_ids.append(notification.id)

    return len(recipient_ids), created_ids
