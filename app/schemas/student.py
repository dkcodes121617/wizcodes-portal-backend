"""Request/response shapes for student enrollment and profile."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class EnrollmentRequest(BaseModel):
    domain_id: UUID
    internship_plan_id: UUID
    chosen_duration_weeks: int = Field(gt=0)
    college: str = Field(min_length=1, max_length=255)
    year_of_study: str = Field(min_length=1, max_length=64)
    certificate_name: str = Field(min_length=1, max_length=255)
    internship_start_date: date
    internship_end_date: date

    @model_validator(mode="after")
    def strip_text_fields(self) -> EnrollmentRequest:
        self.college = self.college.strip()
        self.year_of_study = self.year_of_study.strip()
        self.certificate_name = self.certificate_name.strip()
        if not self.college:
            raise ValueError("College is required")
        if not self.year_of_study:
            raise ValueError("Year of study is required")
        if not self.certificate_name:
            raise ValueError("Full name for certificate is required")
        if self.internship_end_date < self.internship_start_date:
            raise ValueError("End date must be on or after the start date")
        max_end = self.internship_start_date + timedelta(weeks=self.chosen_duration_weeks)
        if self.internship_end_date > max_end:
            raise ValueError(
                "End date must be within the selected internship duration "
                f"(up to {max_end.strftime('%d/%m/%Y')})"
            )
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
    certificate_name: str | None = None
    internship_start_date: date | None = None
    internship_end_date: date | None = None
    payment_screenshot_url: str | None = None
    access_status: str
    access_granted_by: str | None = None
    created_at: datetime
    updated_at: datetime
