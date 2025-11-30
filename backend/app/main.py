"""
FaceLogix Backend API - Main Application Entry Point.

This module initializes the FastAPI application with all necessary
middleware, routers, and lifecycle handlers.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import engine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.
    
    Manages startup and shutdown events for the application.
    """
    # Startup
    logger.info("Starting FaceLogix API...")
    logger.info(f"Debug mode: {settings.DEBUG}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down FaceLogix API...")
    await engine.dispose()
    logger.info("Database connections closed.")


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
async def global_exception_handler(request: Request, exc: Exception):
    """Handle uncaught exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": "Internal server error",
            "detail": str(exc) if settings.DEBUG else None,
        },
    )


# Include API routers
app.include_router(api_router, prefix="/api/v1")


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint.
    
    Returns the health status of the API. Use this endpoint for
    load balancer health checks and monitoring.
    """
    return {
        "status": "healthy",
        "service": "facelogix-api",
        "version": "1.0.0",
    }


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
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
        "health": "/health",
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info",
    )
