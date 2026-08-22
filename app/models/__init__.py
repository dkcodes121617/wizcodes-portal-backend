"""ORM models live here. Import them in this file so they register on Base.metadata."""

from app.db.base import Base
from app.models.internship_plan import InternshipPlan
from app.models.student import Student
from app.models.task import Task

__all__ = ["Base", "InternshipPlan", "Student", "Task"]
