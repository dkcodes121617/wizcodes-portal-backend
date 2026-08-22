"""Request/response shapes for internship tasks."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class TaskCreateRequest(BaseModel):
    domain_id: UUID
    internship_plan_id: UUID
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1)
    github_link: str = Field(min_length=1, max_length=2048)

    @model_validator(mode="after")
    def strip_fields(self) -> TaskCreateRequest:
        self.title = self.title.strip()
        self.description = self.description.strip()
        self.github_link = self.github_link.strip()
        if not self.title:
            raise ValueError("Title is required")
        if not self.description:
            raise ValueError("Description is required")
        if not self.github_link:
            raise ValueError("GitHub link is required")
        return self


class TaskUpdateRequest(BaseModel):
    domain_id: UUID | None = None
    internship_plan_id: UUID | None = None
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, min_length=1)
    github_link: str | None = Field(default=None, min_length=1, max_length=2048)
    is_active: bool | None = None

    @model_validator(mode="after")
    def validate_update(self) -> TaskUpdateRequest:
        fields = (
            self.domain_id,
            self.internship_plan_id,
            self.title,
            self.description,
            self.github_link,
            self.is_active,
        )
        if all(value is None for value in fields):
            raise ValueError("At least one field must be provided")
        if self.title is not None:
            self.title = self.title.strip()
            if not self.title:
                raise ValueError("Title cannot be empty")
        if self.description is not None:
            self.description = self.description.strip()
            if not self.description:
                raise ValueError("Description cannot be empty")
        if self.github_link is not None:
            self.github_link = self.github_link.strip()
            if not self.github_link:
                raise ValueError("GitHub link cannot be empty")
        return self


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    domain_id: UUID
    internship_plan_id: UUID
    title: str
    description: str
    github_link: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
