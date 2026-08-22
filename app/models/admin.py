"""Admin account model."""

from __future__ import annotations

import uuid

from sqlalchemy import CheckConstraint, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class Admin(Base, TimestampMixin):
    __tablename__ = "admins"
    __table_args__ = (
        CheckConstraint(
            "role IN ('admin', 'super_admin')",
            name="admins_role_valid",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default=text("'admin'"),
    )
