"""Public read-only listing for internship domains."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.domain import Domain
from app.schemas.domain import DomainResponse

router = APIRouter(prefix="/domains", tags=["domains"])


@router.get(
    "",
    response_model=list[DomainResponse],
    summary="List active internship domains (public)",
)
async def list_active_domains(
    session: AsyncSession = Depends(get_session),
) -> list[DomainResponse]:
    result = await session.execute(
        select(Domain).where(Domain.is_active.is_(True)).order_by(Domain.name)
    )
    return [DomainResponse.model_validate(row) for row in result.scalars().all()]
