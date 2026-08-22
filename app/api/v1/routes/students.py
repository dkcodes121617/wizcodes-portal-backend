"""Logged-in student actions (enrollment, etc.)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_student
from app.db.session import get_session
from app.models.internship_plan import InternshipPlan
from app.models.student import Student
from app.models.student_task_assignment import StudentTaskAssignment
from app.models.task import Task
from app.schemas.student import EnrollmentRequest, StudentResponse
from app.schemas.student_task_assignment import (
    StudentTaskAssignmentResponse,
    SubmitTaskRequest,
)
from app.services.payment_screenshot_storage import (
    PaymentScreenshotError,
    delete_payment_screenshot,
    save_payment_screenshot,
)
from app.services.student_tasks import build_assignment_response, list_assignments_for_student

router = APIRouter(prefix="/student", tags=["student"])


async def _get_active_domain(session: AsyncSession, domain_id: uuid.UUID) -> None:
    result = await session.execute(
        text("SELECT is_active FROM domains WHERE id = :domain_id"),
        {"domain_id": domain_id},
    )
    row = result.first()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Domain not found",
        )
    if not row[0]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Domain is not available",
        )


async def _get_active_plan(session: AsyncSession, plan_id: uuid.UUID) -> InternshipPlan:
    result = await session.execute(select(InternshipPlan).where(InternshipPlan.id == plan_id))
    plan = result.scalar_one_or_none()
    if plan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Internship plan not found",
        )
    if not plan.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Internship plan is not available",
        )
    return plan


def _validate_duration(plan: InternshipPlan, chosen_duration_weeks: int) -> None:
    if not plan.min_duration_weeks <= chosen_duration_weeks <= plan.max_duration_weeks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Duration must be between {plan.min_duration_weeks} and "
                f"{plan.max_duration_weeks} weeks for this plan."
            ),
        )


@router.post(
    "/enroll",
    response_model=StudentResponse,
    summary="Enroll or update enrollment choices",
)
async def enroll_student(
    body: EnrollmentRequest,
    student: Student = Depends(get_current_student),
    session: AsyncSession = Depends(get_session),
) -> StudentResponse:
    await _get_active_domain(session, body.domain_id)
    plan = await _get_active_plan(session, body.internship_plan_id)
    _validate_duration(plan, body.chosen_duration_weeks)

    student.domain_id = body.domain_id
    student.internship_plan_id = body.internship_plan_id
    student.chosen_duration_weeks = body.chosen_duration_weeks
    student.college = body.college
    student.year_of_study = body.year_of_study

    await session.commit()
    await session.refresh(student)
    return StudentResponse.model_validate(student)


@router.post(
    "/payment-screenshot",
    response_model=StudentResponse,
    summary="Upload a payment screenshot",
)
async def upload_payment_screenshot(
    file: UploadFile = File(...),
    student: Student = Depends(get_current_student),
    session: AsyncSession = Depends(get_session),
) -> StudentResponse:
    try:
        relative_path = await save_payment_screenshot(student.id, file)
    except PaymentScreenshotError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.message,
        ) from exc

    previous_path = student.payment_screenshot_url
    student.payment_screenshot_url = relative_path

    await session.commit()
    await session.refresh(student)

    if previous_path and previous_path != relative_path:
        delete_payment_screenshot(previous_path)

    return StudentResponse.model_validate(student)


@router.get(
    "/my-tasks",
    response_model=list[StudentTaskAssignmentResponse],
    summary="List the current student's assigned tasks",
)
async def list_my_tasks(
    student: Student = Depends(get_current_student),
    session: AsyncSession = Depends(get_session),
) -> list[StudentTaskAssignmentResponse]:
    return await list_assignments_for_student(session, student.id)


@router.patch(
    "/my-tasks/{assignment_id}/submit",
    response_model=StudentTaskAssignmentResponse,
    summary="Submit work for an assigned task",
)
async def submit_my_task(
    assignment_id: uuid.UUID,
    body: SubmitTaskRequest,
    student: Student = Depends(get_current_student),
    session: AsyncSession = Depends(get_session),
) -> StudentTaskAssignmentResponse:
    result = await session.execute(
        select(StudentTaskAssignment, Task)
        .join(Task, StudentTaskAssignment.task_id == Task.id)
        .where(
            StudentTaskAssignment.id == assignment_id,
            StudentTaskAssignment.student_id == student.id,
        )
    )
    row = result.first()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found",
        )

    assignment, task = row
    assignment.submission_link = str(body.submission_link)
    assignment.submitted_at = datetime.now(UTC)
    assignment.status = "submitted"

    await session.commit()
    await session.refresh(assignment)
    return build_assignment_response(assignment, task)
