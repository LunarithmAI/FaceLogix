"""
API v1 Router - Aggregates all endpoint routers.
"""

from fastapi import APIRouter

from app.api.v1 import (
    attendance,
    auth,
    calendar,
    devices,
    reports,
    settings,
    shifts,
    units,
    users,
)

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(units.router)
api_router.include_router(shifts.router)
api_router.include_router(calendar.router)
api_router.include_router(devices.router)
api_router.include_router(attendance.router)
api_router.include_router(reports.router)
api_router.include_router(settings.router)
