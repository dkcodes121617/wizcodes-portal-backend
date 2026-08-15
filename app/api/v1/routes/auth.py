"""Student signup, login, and session introspection."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import STUDENT_ROLE, get_current_student
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_session
from app.models.student import Student
from app.schemas.auth import (
    StudentLoginRequest,
    StudentResponse,
    StudentSignupRequest,
    TokenResponse,
)

router = APIRouter(prefix="/auth/student", tags=["auth"])


def _token_for_student(student: Student) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(str(student.id), role=STUDENT_ROLE),
    )


async def _find_by_identifier(
    session: AsyncSession,
    *,
    email: str | None,
    phone: str | None,
) -> Student | None:
    if email is None and phone is None:
        return None

    clauses = []
    if email is not None:
        clauses.append(Student.email == email)
    if phone is not None:
        clauses.append(Student.phone == phone)

    result = await session.execute(select(Student).where(or_(*clauses)))
    return result.scalar_one_or_none()


async def _conflicting_student(
    session: AsyncSession,
    *,
    email: str | None,
    phone: str | None,
) -> bool:
    clauses = []
    if email is not None:
        clauses.append(Student.email == email)
    if phone is not None:
        clauses.append(Student.phone == phone)
    if not clauses:
        return False

    result = await session.execute(select(Student.id).where(or_(*clauses)).limit(1))
    return result.scalar_one_or_none() is not None


@router.post(
    "/signup",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a student account",
)
async def student_signup(
    body: StudentSignupRequest,
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    if await _conflicting_student(session, email=body.email, phone=body.phone):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email or phone is already registered.",
        )

    student = Student(
        name=body.name.strip(),
        email=body.email,
        phone=body.phone,
        password_hash=hash_password(body.password),
    )
    session.add(student)
    await session.commit()
    await session.refresh(student)
    return _token_for_student(student)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Log in with email or phone",
)
async def student_login(
    body: StudentLoginRequest,
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    student = await _find_by_identifier(
        session,
        email=body.lookup_email,
        phone=body.lookup_phone,
    )
    if student is None or not verify_password(body.password, student.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    return _token_for_student(student)


@router.get(
    "/me",
    response_model=StudentResponse,
    summary="Current student profile",
)
async def student_me(
    student: Student = Depends(get_current_student),
) -> StudentResponse:
    return StudentResponse.model_validate(student)
