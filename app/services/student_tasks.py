"""Shared helpers for reading student task assignments."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.student_task_assignment import StudentTaskAssignment
from app.models.task import Task
from app.schemas.student_task_assignment import (
    AssignedTaskDetails,
    StudentTaskAssignmentResponse,
)


def build_assignment_response(
    assignment: StudentTaskAssignment,
    task: Task,
) -> StudentTaskAssignmentResponse:
    return StudentTaskAssignmentResponse(
        id=assignment.id,
        student_id=assignment.student_id,
        task_id=assignment.task_id,
        assigned_at=assignment.assigned_at,
        assigned_by=assignment.assigned_by,
        status=assignment.status,
        submission_link=assignment.submission_link,
        submitted_at=assignment.submitted_at,
        admin_feedback=assignment.admin_feedback,
        created_at=assignment.created_at,
        updated_at=assignment.updated_at,
        task=AssignedTaskDetails.model_validate(task),
    )


async def list_assignments_for_student(
    session: AsyncSession,
    student_id: uuid.UUID,
) -> list[StudentTaskAssignmentResponse]:
    result = await session.execute(
        select(StudentTaskAssignment, Task)
        .join(Task, StudentTaskAssignment.task_id == Task.id)
        .where(StudentTaskAssignment.student_id == student_id)
        .order_by(StudentTaskAssignment.assigned_at.asc())
    )
    return [
        build_assignment_response(assignment, task)
        for assignment, task in result.all()
    ]
