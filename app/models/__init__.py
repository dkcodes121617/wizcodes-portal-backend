"""ORM models live here. Import them in this file so they register on Base.metadata."""

from app.db.base import Base
from app.models.student import Student

__all__ = ["Base", "Student"]
