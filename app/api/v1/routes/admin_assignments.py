"""Admin review queue and submission review for task assignments."""

from __future__ import annotations

import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_admin
from app.db.session import get_session
from app.models.student import Student
from app.models.student_task_assignment import StudentTaskAssignment
from app.models.task import Task
from app.schemas.student_task_assignment import (
    AdminAssignmentQueueItem,
    ReviewSubmissionRequest,
    StudentTaskAssignmentResponse,
)
from app.services.student_tasks import build_assignment_response

router = APIRouter(
    prefix="/admin/assignments",
    tags=["admin-assignments"],
    dependencies=[Depends(get_current_admin)],
)

AssignmentStatusFilter = Literal["assigned", "in_progress", "submitted", "completed"]


async def _get_assignment_or_404(
    session: AsyncSession,
    assignment_id: uuid.UUID,
) -> tuple[StudentTaskAssignment, Task]:
    result = await session.execute(
        select(StudentTaskAssignment, Task)
        .join(Task, StudentTaskAssignment.task_id == Task.id)
        .where(StudentTaskAssignment.id == assignment_id)
    )
    row = result.first()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found",
        )
    return row[0], row[1]


@router.get(
    "",
    response_model=list[AdminAssignmentQueueItem],
    summary="List assignments across all students (optional status filter)",
)
async def list_assignments_admin(
    status_filter: AssignmentStatusFilter | None = Query(
        default=None,
        alias="status",
        description="Filter by assignment status, e.g. submitted for the review queue",
    ),
    session: AsyncSession = Depends(get_session),
) -> list[AdminAssignmentQueueItem]:
    query = (
        select(StudentTaskAssignment, Task, Student)
        .join(Task, StudentTaskAssignment.task_id == Task.id)
        .join(Student, StudentTaskAssignment.student_id == Student.id)
    )
    if status_filter is not None:
        query = query.where(StudentTaskAssignment.status == status_filter)
    query = query.order_by(StudentTaskAssignment.submitted_at.desc().nullslast())
    result = await session.execute(query)
    return [
        AdminAssignmentQueueItem(
            **build_assignment_response(assignment, task).model_dump(),
            student_name=student.name,
        )
        for assignment, task, student in result.all()
    ]


@router.patch(
    "/{assignment_id}/review",
    response_model=StudentTaskAssignmentResponse,
    summary="Review a submitted assignment",
)
async def review_assignment(
    assignment_id: uuid.UUID,
    body: ReviewSubmissionRequest,
    session: AsyncSession = Depends(get_session),
) -> StudentTaskAssignmentResponse:
    assignment, task = await _get_assignment_or_404(session, assignment_id)

    if assignment.status == "completed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This assignment has already been marked completed.",
        )

    if assignment.status != "submitted":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only submitted assignments can be reviewed.",
        )

    assignment.status = body.status
    if "admin_feedback" in body.model_fields_set:
        assignment.admin_feedback = body.admin_feedback

    await session.commit()
    await session.refresh(assignment)
    return build_assignment_response(assignment, task)
