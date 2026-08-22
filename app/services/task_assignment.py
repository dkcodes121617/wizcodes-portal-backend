"""Business logic for assigning internship tasks to students."""

from __future__ import annotations

import random
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.internship_plan import InternshipPlan
from app.models.student import Student
from app.models.student_task_assignment import StudentTaskAssignment
from app.models.task import Task

BASIC_TIER = "basic_299"
PREMIUM_TIER = "premium_999"
SYSTEM_ASSIGNED_BY = "system"


class TaskAssignmentError(Exception):
    """Raised when automatic task assignment cannot complete."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


async def auto_assign_basic_tasks(
    student: Student,
    session: AsyncSession,
) -> list[StudentTaskAssignment]:
    """Randomly assign Basic-plan tasks when access is granted.

    Safe to call for any student: Premium plans are ignored. Basic students
    without enough tasks in the bank raise ``TaskAssignmentError``.
    """
    if student.internship_plan_id is None:
        return []

    plan_result = await session.execute(
        select(InternshipPlan).where(InternshipPlan.id == student.internship_plan_id)
    )
    plan = plan_result.scalar_one_or_none()
    if plan is None or plan.tier != BASIC_TIER:
        return []

    if student.domain_id is None or student.chosen_duration_weeks is None:
        raise TaskAssignmentError(
            "Cannot auto-assign tasks: student enrollment is incomplete.",
        )

    needed = student.chosen_duration_weeks
    tasks_result = await session.execute(
        select(Task).where(
            Task.domain_id == student.domain_id,
            Task.internship_plan_id == student.internship_plan_id,
            Task.is_active.is_(True),
        )
    )
    available_tasks = list(tasks_result.scalars().all())

    available_count = len(available_tasks)
    if available_count < needed:
        raise TaskAssignmentError(
            f"Cannot grant access: only {available_count} tasks available for this "
            f"domain/plan, but student requested {needed} weeks.",
        )

    selected_tasks = random.sample(available_tasks, needed)
    assignments: list[StudentTaskAssignment] = []
    for task in selected_tasks:
        assignment = StudentTaskAssignment(
            student_id=student.id,
            task_id=task.id,
            assigned_by=SYSTEM_ASSIGNED_BY,
        )
        session.add(assignment)
        assignments.append(assignment)

    return assignments


async def manual_assign_premium_tasks(
    student: Student,
    task_ids: list[uuid.UUID],
    admin_id: str,
    session: AsyncSession,
) -> tuple[int, int]:
    """Manually assign Premium-plan tasks to a student with granted access."""
    if student.internship_plan_id is None:
        raise TaskAssignmentError("Student has no internship plan.")

    plan_result = await session.execute(
        select(InternshipPlan).where(InternshipPlan.id == student.internship_plan_id)
    )
    plan = plan_result.scalar_one_or_none()
    if plan is None or plan.tier != PREMIUM_TIER:
        raise TaskAssignmentError(
            "Manual task assignment is only available for Premium students.",
        )

    if student.access_status != "granted":
        raise TaskAssignmentError(
            "Cannot assign tasks until the student's access has been granted.",
        )

    if student.domain_id is None:
        raise TaskAssignmentError("Student has no domain selected.")

    unique_task_ids = list(dict.fromkeys(task_ids))
    tasks_result = await session.execute(select(Task).where(Task.id.in_(unique_task_ids)))
    tasks_by_id = {task.id: task for task in tasks_result.scalars().all()}

    invalid_ids: list[str] = []
    for task_id in unique_task_ids:
        task = tasks_by_id.get(task_id)
        if task is None:
            invalid_ids.append(str(task_id))
            continue
        if not task.is_active:
            invalid_ids.append(str(task_id))
            continue
        if (
            task.domain_id != student.domain_id
            or task.internship_plan_id != student.internship_plan_id
        ):
            invalid_ids.append(str(task_id))

    if invalid_ids:
        raise TaskAssignmentError(f"Invalid task id(s): {', '.join(invalid_ids)}")

    existing_result = await session.execute(
        select(StudentTaskAssignment.task_id).where(
            StudentTaskAssignment.student_id == student.id,
            StudentTaskAssignment.task_id.in_(unique_task_ids),
        )
    )
    already_assigned_ids = set(existing_result.scalars().all())

    newly_created = 0
    already_assigned = 0
    for task_id in unique_task_ids:
        if task_id in already_assigned_ids:
            already_assigned += 1
            continue
        session.add(
            StudentTaskAssignment(
                student_id=student.id,
                task_id=task_id,
                assigned_by=admin_id,
            )
        )
        newly_created += 1

    return newly_created, already_assigned
