"""Request/response shapes for student task assignments."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

AssignmentReviewStatus = Literal["completed", "in_progress"]
AssignmentStatus = Literal["assigned", "in_progress", "submitted", "completed"]


class AssignedTaskDetails(BaseModel):
    """Task fields inlined for assignment list views (student/admin)."""

    model_config = ConfigDict(from_attributes=True)

    title: str
    description: str
    github_link: str


class StudentTaskAssignmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    student_id: UUID
    task_id: UUID
    assigned_at: datetime
    assigned_by: str
    status: str
    submission_link: str | None = None
    submitted_at: datetime | None = None
    admin_feedback: str | None = None
    created_at: datetime
    updated_at: datetime
    task: AssignedTaskDetails


class ManualAssignRequest(BaseModel):
    task_ids: list[UUID] = Field(min_length=1)


class SubmitTaskRequest(BaseModel):
    submission_link: HttpUrl

    @field_validator("submission_link", mode="before")
    @classmethod
    def strip_submission_link(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                raise ValueError("Submission link is required")
            return stripped
        return value


class ManualAssignTasksResponse(BaseModel):
    newly_created: int
    already_assigned: int
    assignments: list[StudentTaskAssignmentResponse]


class ReviewSubmissionRequest(BaseModel):
    status: AssignmentReviewStatus
    admin_feedback: str | None = None

    @field_validator("admin_feedback", mode="before")
    @classmethod
    def strip_admin_feedback(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value


class AdminAssignmentQueueItem(StudentTaskAssignmentResponse):
    student_name: str
