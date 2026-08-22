"""ORM models live here. Import them in this file so they register on Base.metadata."""

from app.db.base import Base
from app.models.admin import Admin
from app.models.internship_plan import InternshipPlan
from app.models.student import Student
from app.models.student_task_assignment import StudentTaskAssignment
from app.models.task import Task

__all__ = ["Admin", "Base", "InternshipPlan", "Student", "StudentTaskAssignment", "Task"]
