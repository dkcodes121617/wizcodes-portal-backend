"""Admin login, session introspection, and account creation."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_admin, get_current_super_admin
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_session
from app.models.admin import Admin
from app.schemas.admin import AdminCreateRequest, AdminLoginRequest, AdminResponse
from app.schemas.auth import TokenResponse

router = APIRouter(prefix="/auth/admin", tags=["admin-auth"])


def _token_for_admin(admin: Admin) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(str(admin.id), role=admin.role),
    )


async def _get_admin_by_email(session: AsyncSession, email: str) -> Admin | None:
    result = await session.execute(select(Admin).where(Admin.email == email))
    return result.scalar_one_or_none()


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Log in as an admin",
)
async def admin_login(
    body: AdminLoginRequest,
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    admin = await _get_admin_by_email(session, body.email)
    if admin is None or not verify_password(body.password, admin.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    return _token_for_admin(admin)


@router.get(
    "/me",
    response_model=AdminResponse,
    summary="Current admin profile",
)
async def admin_me(
    admin: Admin = Depends(get_current_admin),
) -> AdminResponse:
    return AdminResponse.model_validate(admin)


@router.post(
    "/create",
    response_model=AdminResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new admin account (super_admin only)",
)
async def create_admin(
    body: AdminCreateRequest,
    _: Admin = Depends(get_current_super_admin),
    session: AsyncSession = Depends(get_session),
) -> AdminResponse:
    if await _get_admin_by_email(session, body.email) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An admin with this email already exists.",
        )

    admin = Admin(
        name=body.name,
        email=body.email,
        password_hash=hash_password(body.password),
        role=body.role,
    )
    session.add(admin)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An admin with this email already exists.",
        ) from None
    await session.refresh(admin)
    return AdminResponse.model_validate(admin)
