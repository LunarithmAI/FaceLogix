"""
API v1 Router - Aggregates all endpoint routers.
"""

from fastapi import APIRouter

from app.api.v1 import attendance, auth, devices, reports, users

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(devices.router)
api_router.include_router(attendance.router)
api_router.include_router(reports.router)
