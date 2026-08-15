"""Request/response shapes for student authentication."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_PHONE_RE = re.compile(r"^\+?[\d\s\-()]{5,31}$")


def _normalize_email(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip().lower()
    return cleaned or None


def _normalize_phone(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = re.sub(r"\s+", "", value.strip())
    return cleaned or None


class StudentSignupRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    email: str | None = None
    phone: str | None = Field(default=None, max_length=32)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str | None) -> str | None:
        normalized = _normalize_email(value)
        if normalized is None:
            return None
        if not _EMAIL_RE.match(normalized):
            raise ValueError("Invalid email address")
        return normalized

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str | None) -> str | None:
        normalized = _normalize_phone(value)
        if normalized is None:
            return None
        if not _PHONE_RE.match(normalized):
            raise ValueError("Invalid phone number")
        return normalized

    @model_validator(mode="after")
    def require_email_or_phone(self) -> StudentSignupRequest:
        if not self.email and not self.phone:
            raise ValueError("At least one of email or phone is required")
        return self


class StudentLoginRequest(BaseModel):
    identifier: str = Field(min_length=1, max_length=320)
    password: str = Field(min_length=1, max_length=128)

    @property
    def lookup_email(self) -> str | None:
        if "@" in self.identifier:
            return _normalize_email(self.identifier)
        return None

    @property
    def lookup_phone(self) -> str | None:
        if "@" in self.identifier:
            return None
        return _normalize_phone(self.identifier)


class StudentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    email: str | None
    phone: str | None
    created_at: datetime
    updated_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"  # noqa: S105
