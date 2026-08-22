"""Admin CRUD for the shared internship task bank."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_admin
from app.db.session import get_session
from app.models.internship_plan import InternshipPlan
from app.models.task import Task
from app.schemas.task import TaskCreateRequest, TaskResponse, TaskUpdateRequest

router = APIRouter(
    prefix="/admin/tasks",
    tags=["admin-tasks"],
    dependencies=[Depends(get_current_admin)],
)


async def _get_task_or_404(session: AsyncSession, task_id: uuid.UUID) -> Task:
    result = await session.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )
    return task


async def _ensure_domain_exists(session: AsyncSession, domain_id: uuid.UUID) -> None:
    result = await session.execute(
        text("SELECT 1 FROM domains WHERE id = :domain_id LIMIT 1"),
        {"domain_id": domain_id},
    )
    if result.first() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Domain not found",
        )


async def _ensure_plan_exists(session: AsyncSession, plan_id: uuid.UUID) -> None:
    result = await session.execute(select(InternshipPlan.id).where(InternshipPlan.id == plan_id))
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Internship plan not found",
        )


PREMIUM_TIER = "premium_999"


async def _get_premium_plan_id(session: AsyncSession) -> uuid.UUID:
    result = await session.execute(
        select(InternshipPlan.id).where(InternshipPlan.tier == PREMIUM_TIER)
    )
    plan_id = result.scalar_one_or_none()
    if plan_id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Premium internship plan not found",
        )
    return plan_id


async def _list_tasks_filtered(
    session: AsyncSession,
    *,
    domain_id: uuid.UUID | None = None,
    internship_plan_id: uuid.UUID | None = None,
) -> list[TaskResponse]:
    query = select(Task)
    if domain_id is not None:
        query = query.where(Task.domain_id == domain_id)
    if internship_plan_id is not None:
        query = query.where(Task.internship_plan_id == internship_plan_id)
    query = query.order_by(Task.created_at.desc())
    result = await session.execute(query)
    return [TaskResponse.model_validate(row) for row in result.scalars().all()]


@router.post(
    "",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a task",
)
async def create_task(
    body: TaskCreateRequest,
    session: AsyncSession = Depends(get_session),
) -> TaskResponse:
    await _ensure_domain_exists(session, body.domain_id)
    await _ensure_plan_exists(session, body.internship_plan_id)

    task = Task(
        domain_id=body.domain_id,
        internship_plan_id=body.internship_plan_id,
        title=body.title,
        description=body.description,
        github_link=body.github_link,
    )
    session.add(task)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Domain or internship plan not found",
        ) from None
    await session.refresh(task)
    return TaskResponse.model_validate(task)


@router.get(
    "",
    response_model=list[TaskResponse],
    summary="List tasks (optional domain_id / internship_plan_id filters)",
)
async def list_tasks_admin(
    domain_id: uuid.UUID | None = Query(default=None),
    internship_plan_id: uuid.UUID | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> list[TaskResponse]:
    return await _list_tasks_filtered(
        session,
        domain_id=domain_id,
        internship_plan_id=internship_plan_id,
    )


@router.get(
    "/premium",
    response_model=list[TaskResponse],
    summary="List Premium-tier tasks (optional domain_id filter)",
)
async def list_premium_tasks_admin(
    domain_id: uuid.UUID | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> list[TaskResponse]:
    premium_plan_id = await _get_premium_plan_id(session)
    return await _list_tasks_filtered(
        session,
        domain_id=domain_id,
        internship_plan_id=premium_plan_id,
    )


@router.get(
    "/{task_id}",
    response_model=TaskResponse,
    summary="Get a task by id",
)
async def get_task_admin(
    task_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> TaskResponse:
    task = await _get_task_or_404(session, task_id)
    return TaskResponse.model_validate(task)


@router.patch(
    "/{task_id}",
    response_model=TaskResponse,
    summary="Update a task",
)
async def update_task(
    task_id: uuid.UUID,
    body: TaskUpdateRequest,
    session: AsyncSession = Depends(get_session),
) -> TaskResponse:
    task = await _get_task_or_404(session, task_id)

    if body.domain_id is not None:
        await _ensure_domain_exists(session, body.domain_id)
        task.domain_id = body.domain_id
    if body.internship_plan_id is not None:
        await _ensure_plan_exists(session, body.internship_plan_id)
        task.internship_plan_id = body.internship_plan_id
    if body.title is not None:
        task.title = body.title
    if body.description is not None:
        task.description = body.description
    if body.github_link is not None:
        task.github_link = body.github_link
    if body.is_active is not None:
        task.is_active = body.is_active

    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Domain or internship plan not found",
        ) from None
    await session.refresh(task)
    return TaskResponse.model_validate(task)


@router.delete(
    "/{task_id}",
    response_model=TaskResponse,
    summary="Soft-delete a task (sets is_active to false)",
)
async def soft_delete_task(
    task_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> TaskResponse:
    task = await _get_task_or_404(session, task_id)
    task.is_active = False
    await session.commit()
    await session.refresh(task)
    return TaskResponse.model_validate(task)
