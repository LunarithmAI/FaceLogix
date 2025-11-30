"""
API Router aggregating all v1 endpoints.

Combines embedding, detection, and liveness endpoints into
a single router for inclusion in the main application.
"""

from fastapi import APIRouter

from app.api.v1 import detect, embed, liveness

api_router = APIRouter()

# Include individual endpoint routers with their tags
api_router.include_router(
    embed.router,
    tags=["Embedding"]
)
api_router.include_router(
    detect.router,
    tags=["Detection"]
)
api_router.include_router(
    liveness.router,
    tags=["Liveness"]
)
