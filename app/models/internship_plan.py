"""Internship plan model (e.g. Basic ₹299, Premium ₹999)."""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, CheckConstraint, Integer, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class InternshipPlan(Base, TimestampMixin):
    __tablename__ = "internship_plans"
    __table_args__ = (
        CheckConstraint(
            "min_duration_weeks <= max_duration_weeks",
            name="internship_plans_duration_range_valid",
        ),
        CheckConstraint("price > 0", name="internship_plans_price_positive"),
        CheckConstraint(
            "min_duration_weeks > 0 AND max_duration_weeks > 0",
            name="internship_plans_duration_positive",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    tier: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    price: Mapped[int] = mapped_column(Integer, nullable=False)
    min_duration_weeks: Mapped[int] = mapped_column(Integer, nullable=False)
    max_duration_weeks: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
