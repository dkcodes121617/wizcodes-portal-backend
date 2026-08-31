"""Admin notification sending."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_admin
from app.db.session import get_session
from app.models.admin import Admin
from app.schemas.notification import NotificationSendRequest, NotificationSendResponse
from app.services.notifications import send_notifications

router = APIRouter(
    prefix="/admin/notifications",
    tags=["admin-notifications"],
    dependencies=[Depends(get_current_admin)],
)


@router.post(
    "/send",
    response_model=NotificationSendResponse,
    summary="Send a notification to one student or a group",
)
async def send_notification(
    body: NotificationSendRequest,
    admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session),
) -> NotificationSendResponse:
    recipients, notification_ids = await send_notifications(session, admin.id, body)
    if recipients == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No matching recipients found for this notification.",
        )
    await session.commit()
    return NotificationSendResponse(
        recipients=recipients,
        notification_ids=notification_ids,
    )
