"""Admin CRUD and public read-only listing for internship plans."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_admin_placeholder
from app.db.session import get_session
from app.models.internship_plan import InternshipPlan
from app.schemas.internship_plan import (
    InternshipPlanCreateRequest,
    InternshipPlanResponse,
    InternshipPlanUpdateRequest,
)

admin_router = APIRouter(
    prefix="/admin/internship-plans",
    tags=["admin-internship-plans"],
    dependencies=[Depends(get_current_admin_placeholder)],
)
public_router = APIRouter(prefix="/internship-plans", tags=["internship-plans"])


async def _get_plan_or_404(session: AsyncSession, plan_id: uuid.UUID) -> InternshipPlan:
    result = await session.execute(select(InternshipPlan).where(InternshipPlan.id == plan_id))
    plan = result.scalar_one_or_none()
    if plan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Internship plan not found",
        )
    return plan


async def _tier_taken(
    session: AsyncSession,
    tier: str,
    *,
    exclude_id: uuid.UUID | None = None,
) -> bool:
    query = select(InternshipPlan.id).where(InternshipPlan.tier == tier)
    if exclude_id is not None:
        query = query.where(InternshipPlan.id != exclude_id)
    result = await session.execute(query.limit(1))
    return result.scalar_one_or_none() is not None


def _validate_duration_range(min_weeks: int, max_weeks: int) -> None:
    if min_weeks > max_weeks:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="min_duration_weeks must be less than or equal to max_duration_weeks",
        )


@admin_router.post(
    "",
    response_model=InternshipPlanResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an internship plan",
)
async def create_internship_plan(
    body: InternshipPlanCreateRequest,
    session: AsyncSession = Depends(get_session),
) -> InternshipPlanResponse:
    if await _tier_taken(session, body.tier):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An internship plan with this tier already exists.",
        )

    plan = InternshipPlan(
        tier=body.tier,
        price=body.price,
        min_duration_weeks=body.min_duration_weeks,
        max_duration_weeks=body.max_duration_weeks,
    )
    session.add(plan)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An internship plan with this tier already exists.",
        ) from None
    await session.refresh(plan)
    return InternshipPlanResponse.model_validate(plan)


@admin_router.get(
    "",
    response_model=list[InternshipPlanResponse],
    summary="List all internship plans (including inactive)",
)
async def list_internship_plans_admin(
    session: AsyncSession = Depends(get_session),
) -> list[InternshipPlanResponse]:
    result = await session.execute(select(InternshipPlan).order_by(InternshipPlan.tier))
    return [InternshipPlanResponse.model_validate(row) for row in result.scalars().all()]


@admin_router.get(
    "/{plan_id}",
    response_model=InternshipPlanResponse,
    summary="Get an internship plan by id",
)
async def get_internship_plan_admin(
    plan_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> InternshipPlanResponse:
    plan = await _get_plan_or_404(session, plan_id)
    return InternshipPlanResponse.model_validate(plan)


@admin_router.patch(
    "/{plan_id}",
    response_model=InternshipPlanResponse,
    summary="Update an internship plan",
)
async def update_internship_plan(
    plan_id: uuid.UUID,
    body: InternshipPlanUpdateRequest,
    session: AsyncSession = Depends(get_session),
) -> InternshipPlanResponse:
    plan = await _get_plan_or_404(session, plan_id)

    if body.tier is not None and await _tier_taken(session, body.tier, exclude_id=plan_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An internship plan with this tier already exists.",
        )

    if body.tier is not None:
        plan.tier = body.tier
    if body.price is not None:
        plan.price = body.price
    if body.min_duration_weeks is not None:
        plan.min_duration_weeks = body.min_duration_weeks
    if body.max_duration_weeks is not None:
        plan.max_duration_weeks = body.max_duration_weeks
    if body.is_active is not None:
        plan.is_active = body.is_active

    _validate_duration_range(plan.min_duration_weeks, plan.max_duration_weeks)

    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An internship plan with this tier already exists.",
        ) from None
    await session.refresh(plan)
    return InternshipPlanResponse.model_validate(plan)


@admin_router.delete(
    "/{plan_id}",
    response_model=InternshipPlanResponse,
    summary="Soft-delete an internship plan (sets is_active to false)",
)
async def soft_delete_internship_plan(
    plan_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> InternshipPlanResponse:
    plan = await _get_plan_or_404(session, plan_id)
    plan.is_active = False
    await session.commit()
    await session.refresh(plan)
    return InternshipPlanResponse.model_validate(plan)


@public_router.get(
    "",
    response_model=list[InternshipPlanResponse],
    summary="List active internship plans (public)",
)
async def list_active_internship_plans(
    session: AsyncSession = Depends(get_session),
) -> list[InternshipPlanResponse]:
    result = await session.execute(
        select(InternshipPlan)
        .where(InternshipPlan.is_active.is_(True))
        .order_by(InternshipPlan.tier)
    )
    return [InternshipPlanResponse.model_validate(row) for row in result.scalars().all()]
