"""Admin review of student payments and manual access grants."""

from __future__ import annotations

import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_admin
from app.db.session import get_session
from app.models.admin import Admin
from app.models.student import Student
from app.schemas.student import StudentResponse
from app.schemas.student_task_assignment import (
    ManualAssignRequest,
    ManualAssignTasksResponse,
    StudentTaskAssignmentResponse,
)
from app.services.student_tasks import list_assignments_for_student
from app.services.task_assignment import (
    TaskAssignmentError,
    auto_assign_basic_tasks,
    manual_assign_premium_tasks,
)

router = APIRouter(
    prefix="/admin/students",
    tags=["admin-students"],
    dependencies=[Depends(get_current_admin)],
)

StudentAccessStatus = Literal["pending", "granted"]


async def _get_student_or_404(session: AsyncSession, student_id: uuid.UUID) -> Student:
    result = await session.execute(select(Student).where(Student.id == student_id))
    student = result.scalar_one_or_none()
    if student is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found",
        )
    return student


@router.get(
    "/{student_id}/tasks",
    response_model=list[StudentTaskAssignmentResponse],
    summary="List a student's task assignments",
)
async def list_student_tasks_admin(
    student_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> list[StudentTaskAssignmentResponse]:
    await _get_student_or_404(session, student_id)
    return await list_assignments_for_student(session, student_id)


@router.post(
    "/{student_id}/assign-tasks",
    response_model=ManualAssignTasksResponse,
    summary="Manually assign Premium tasks to a student",
)
async def assign_tasks_to_student(
    student_id: uuid.UUID,
    body: ManualAssignRequest,
    admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session),
) -> ManualAssignTasksResponse:
    student = await _get_student_or_404(session, student_id)

    try:
        newly_created, already_assigned = await manual_assign_premium_tasks(
            student,
            body.task_ids,
            str(admin.id),
            session,
        )
    except TaskAssignmentError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.message,
        ) from exc

    await session.commit()
    assignments = await list_assignments_for_student(session, student_id)
    return ManualAssignTasksResponse(
        newly_created=newly_created,
        already_assigned=already_assigned,
        assignments=assignments,
    )


@router.get(
    "",
    response_model=list[StudentResponse],
    summary="List students (optional access_status filter)",
)
async def list_students_admin(
    access_status: StudentAccessStatus | None = Query(
        default=None,
        description="Filter by access status, e.g. pending for payment review queue",
    ),
    session: AsyncSession = Depends(get_session),
) -> list[StudentResponse]:
    query = select(Student)
    if access_status is not None:
        query = query.where(Student.access_status == access_status)
    query = query.order_by(Student.created_at.desc())
    result = await session.execute(query)
    return [StudentResponse.model_validate(row) for row in result.scalars().all()]


@router.get(
    "/{student_id}",
    response_model=StudentResponse,
    summary="Get a student by id",
)
async def get_student_admin(
    student_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> StudentResponse:
    student = await _get_student_or_404(session, student_id)
    return StudentResponse.model_validate(student)


@router.patch(
    "/{student_id}/grant-access",
    response_model=StudentResponse,
    summary="Grant portal access after payment review",
)
async def grant_student_access(
    student_id: uuid.UUID,
    admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session),
) -> StudentResponse:
    student = await _get_student_or_404(session, student_id)

    if not student.payment_screenshot_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot grant access without a payment screenshot.",
        )

    if student.access_status == "granted":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Access has already been granted for this student.",
        )

    student.access_status = "granted"
    student.access_granted_by = str(admin.id)

    try:
        await auto_assign_basic_tasks(student, session)
    except TaskAssignmentError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.message,
        ) from exc

    await session.commit()
    await session.refresh(student)
    return StudentResponse.model_validate(student)
