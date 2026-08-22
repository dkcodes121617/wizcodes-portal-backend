"""Student account model.

Auth fields from A1; enrollment fields (domain, plan, duration, profile) from A6;
payment screenshot and access status from A7.
"""

from __future__ import annotations

import uuid

from sqlalchemy import CheckConstraint, Integer, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class Student(Base, TimestampMixin):
    __tablename__ = "students"
    __table_args__ = (
        CheckConstraint(
            "email IS NOT NULL OR phone IS NOT NULL",
            name="students_email_or_phone_required",
        ),
        CheckConstraint(
            "access_status IN ('pending', 'granted')",
            name="students_access_status_valid",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(320), unique=True, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), unique=True, nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    domain_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    internship_plan_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    chosen_duration_weeks: Mapped[int | None] = mapped_column(Integer, nullable=True)
    college: Mapped[str | None] = mapped_column(String(255), nullable=True)
    year_of_study: Mapped[str | None] = mapped_column(String(64), nullable=True)
    payment_screenshot_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    access_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default=text("'pending'"),
    )
    # TODO(A13): replace with a real FK to admins.id once the Admin table exists.
    access_granted_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
