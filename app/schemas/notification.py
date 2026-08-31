"""Notification request/response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

NotificationAudience = Literal["single", "all", "pending", "granted", "custom"]


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    student_id: UUID
    title: str
    body: str
    read_at: datetime | None
    sent_by_admin_id: UUID | None
    created_at: datetime
    updated_at: datetime


class NotificationUnreadCountResponse(BaseModel):
    unread_count: int


class NotificationSendRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    body: str = Field(min_length=1, max_length=5000)
    audience: NotificationAudience
    student_id: UUID | None = None
    student_ids: list[UUID] | None = None

    @model_validator(mode="after")
    def validate_recipients(self) -> NotificationSendRequest:
        self.title = self.title.strip()
        self.body = self.body.strip()
        if not self.title:
            raise ValueError("Title is required")
        if not self.body:
            raise ValueError("Message is required")

        if self.audience == "single":
            if self.student_id is None:
                raise ValueError("student_id is required for a single recipient")
        elif self.audience == "custom":
            if not self.student_ids:
                raise ValueError("student_ids is required for a custom group")
        return self


class NotificationSendResponse(BaseModel):
    recipients: int
    notification_ids: list[UUID]
