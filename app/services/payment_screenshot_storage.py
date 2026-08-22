"""Local-disk storage for student payment screenshots.

The public API stores a relative path in the database. Swapping to cloud
storage later should only require changing this module's internals.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path

from fastapi import UploadFile

from app.core.config import Settings, get_settings

_BACKEND_ROOT = Path(__file__).resolve().parents[2]

_ALLOWED_CONTENT_TYPES: dict[str, str] = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


class PaymentScreenshotError(Exception):
    """Validation or persistence failure for a payment screenshot upload."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


def _upload_root(settings: Settings) -> Path:
    return _BACKEND_ROOT / settings.PAYMENT_SCREENSHOT_UPLOAD_DIR


def resolve_payment_screenshot_path(relative_path: str) -> Path:
    """Resolve a stored relative path under the backend project root."""
    return _BACKEND_ROOT / relative_path


async def save_payment_screenshot(
    student_id: uuid.UUID,
    upload: UploadFile,
    *,
    settings: Settings | None = None,
) -> str:
    """Validate an image upload and persist it locally.

    Returns the relative path stored in ``payment_screenshot_url``.
    """
    active_settings = settings or get_settings()
    content_type = (upload.content_type or "").split(";", 1)[0].strip().lower()
    extension = _ALLOWED_CONTENT_TYPES.get(content_type)
    if extension is None:
        raise PaymentScreenshotError(
            "Only image uploads are allowed (JPEG, PNG, WebP, or GIF).",
        )

    chunks: list[bytes] = []
    total_size = 0
    while chunk := await upload.read(1024 * 1024):
        total_size += len(chunk)
        if total_size > active_settings.PAYMENT_SCREENSHOT_MAX_BYTES:
            raise PaymentScreenshotError("Payment screenshot must be 10 MB or smaller.")
        chunks.append(chunk)

    if total_size == 0:
        raise PaymentScreenshotError("Uploaded file is empty.")

    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    filename = f"{student_id}_{timestamp}{extension}"
    upload_dir = _upload_root(active_settings)
    upload_dir.mkdir(parents=True, exist_ok=True)
    destination = upload_dir / filename
    destination.write_bytes(b"".join(chunks))

    relative_path = f"{active_settings.PAYMENT_SCREENSHOT_UPLOAD_DIR}/{filename}"
    return relative_path.replace("\\", "/")


def delete_payment_screenshot(relative_path: str | None) -> None:
    """Best-effort delete of a previously stored screenshot."""
    if not relative_path:
        return
    path = resolve_payment_screenshot_path(relative_path)
    if path.is_file():
        path.unlink()
