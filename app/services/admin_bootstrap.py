"""Ensure the configured admin account exists on startup (from env vars)."""

from __future__ import annotations

import logging
import re

from sqlalchemy import func, select

from app.core.config import Settings
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.admin import Admin

logger = logging.getLogger("app.admin_bootstrap")

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _normalise_email(email: str) -> str:
    cleaned = email.strip().lower()
    if not _EMAIL_RE.match(cleaned):
        raise ValueError(f"ADMIN_EMAIL is not a valid email address: {email!r}")
    return cleaned


async def bootstrap_admin_from_env(settings: Settings) -> None:
    """Create or update the single admin account defined in environment variables.

    When ADMIN_EMAIL and ADMIN_PASSWORD are set, the matching admin row is
    created (as super_admin) or its password is refreshed from env. This lets
    Render deployments log in without running a one-off script.
    """
    email_raw = settings.ADMIN_EMAIL
    password = settings.ADMIN_PASSWORD
    if not email_raw or not password:
        if settings.is_production:
            logger.warning(
                "ADMIN_EMAIL and ADMIN_PASSWORD are not set — admin login will not work "
                "until an admin account exists."
            )
        return

    email = _normalise_email(email_raw)
    if len(password) < 8:
        raise ValueError("ADMIN_PASSWORD must be at least 8 characters.")

    name = settings.ADMIN_NAME.strip() or "Admin"
    password_hash = hash_password(password)

    async with SessionLocal() as session:
        result = await session.execute(select(Admin).where(Admin.email == email))
        admin = result.scalar_one_or_none()

        if admin is None:
            admin = Admin(
                name=name,
                email=email,
                password_hash=password_hash,
                role="super_admin",
            )
            session.add(admin)
            await session.commit()
            logger.info("Created super_admin from env: %s", email)
            return

        admin.name = name
        admin.password_hash = password_hash
        if admin.role != "super_admin":
            admin.role = "super_admin"
        await session.commit()
        logger.info("Updated admin credentials from env: %s", email)

        count_result = await session.execute(select(func.count()).select_from(Admin))
        admin_count = count_result.scalar_one()
        if admin_count > 1:
            logger.warning(
                "Multiple admin accounts exist (%s). Only %s is managed via ADMIN_EMAIL env.",
                admin_count,
                email,
            )
