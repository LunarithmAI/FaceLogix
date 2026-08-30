"""
FaceLogix Backend API - Main Application Entry Point.

This module initializes the FastAPI application with all necessary
middleware, routers, and lifecycle handlers.
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import AsyncSessionLocal, engine
from app.services.face_client import FaceServiceClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info("Starting FaceLogix API")
    async with httpx.AsyncClient(
        base_url=settings.FACE_SERVICE_URL.rstrip("/"),
        timeout=settings.FACE_SERVICE_TIMEOUT,
    ) as http_client:
        app.state.face_client = FaceServiceClient(http_client)
        try:
            yield
        finally:
            app.state.face_client = None
            await engine.dispose()
            logger.info("FaceLogix API stopped")


# Create FastAPI application
app = FastAPI(
    title="FaceLogix API",
    description="""
    Face Recognition Attendance System API.
    
    FaceLogix provides a complete solution for managing attendance
    using face recognition technology.
    
    ## Features
    
    - **Authentication**: User and device authentication with JWT tokens
    - **User Management**: Create, update, and manage users with face enrollment
    - **Device Management**: Register and manage check-in devices/kiosks
    - **Attendance Tracking**: Face recognition-based check-in/check-out
    - **Reports**: Attendance reports and analytics
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle uncaught exceptions."""
    logger.exception("Unhandled exception")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": {
                "code": "INTERNAL_ERROR",
                "message": "Internal server error",
            }
        },
    )


# Include API routers
app.include_router(api_router, prefix="/api/v1")


@app.get("/health/live", tags=["Health"])
async def health_live() -> dict[str, str]:
    return {"status": "alive"}


@app.get("/health/ready", tags=["Health"])
async def health_ready(request: Request) -> JSONResponse:
    database_ready = False
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
        database_ready = True
    except Exception:
        logger.exception("Database readiness check failed")

    face_client = getattr(request.app.state, "face_client", None)
    face_ready = isinstance(face_client, FaceServiceClient) and await face_client.ready()
    if not database_ready or not face_ready:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "detail": {
                    "code": "DEPENDENCY_UNAVAILABLE",
                    "message": "Required dependencies are unavailable",
                },
                "database": database_ready,
                "face_service": face_ready,
            },
        )
    return JSONResponse(
        content={
            "status": "ready",
            "database": True,
            "face_service": True,
        }
    )


# Root endpoint
@app.get("/", tags=["Root"])
async def root() -> dict[str, str]:
    """
    Root endpoint.

    Returns basic API information and links to documentation.
    """
    return {
        "name": "FaceLogix API",
        "version": "1.0.0",
        "docs": "/api/docs",
        "redoc": "/api/redoc",
        "openapi": "/api/openapi.json",
        "health": "/health/ready",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",  # noqa: S104 - container service must accept external traffic
        port=8000,
        reload=settings.DEBUG,
        log_level="info",
    )
