from fastapi import APIRouter

from app.api.v1.routes import (
    admin_assignments,
    admin_auth,
    admin_notifications,
    admin_students,
    auth,
    domains,
    health,
    internship_plans,
    notifications,
    students,
    tasks,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(admin_auth.router)
api_router.include_router(students.router)
api_router.include_router(notifications.router)
api_router.include_router(admin_students.router)
api_router.include_router(admin_notifications.router)
api_router.include_router(admin_assignments.router)
api_router.include_router(internship_plans.admin_router)
api_router.include_router(internship_plans.public_router)
api_router.include_router(domains.router)
api_router.include_router(tasks.router)
