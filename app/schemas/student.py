"""Request/response shapes for student enrollment and profile."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class EnrollmentRequest(BaseModel):
    domain_id: UUID
    internship_plan_id: UUID
    chosen_duration_weeks: int = Field(gt=0)
    college: str = Field(min_length=1, max_length=255)
    year_of_study: str = Field(min_length=1, max_length=64)

    @model_validator(mode="after")
    def strip_text_fields(self) -> EnrollmentRequest:
        self.college = self.college.strip()
        self.year_of_study = self.year_of_study.strip()
        if not self.college:
            raise ValueError("College is required")
        if not self.year_of_study:
            raise ValueError("Year of study is required")
        return self


class StudentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    email: str | None
    phone: str | None
    domain_id: UUID | None = None
    internship_plan_id: UUID | None = None
    chosen_duration_weeks: int | None = None
    college: str | None = None
    year_of_study: str | None = None
    payment_screenshot_url: str | None = None
    access_status: str
    access_granted_by: str | None = None
    created_at: datetime
    updated_at: datetime
