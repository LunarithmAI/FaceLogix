"""
FastAPI application for Face Recognition Service.

Provides endpoints for face detection, embedding generation,
and liveness detection with model preloading on startup.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.models.loader import ModelLoader


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    
    Handles startup and shutdown events:
    - Startup: Load and warm up ML models
    - Shutdown: Clean up resources
    """
    # Startup: Load and warm up models
    print(f"Starting {settings.SERVICE_NAME}...")
    print("Loading ML models...")
    try:
        ModelLoader.warmup()
        print("Models loaded and warmed up successfully")
    except FileNotFoundError as e:
        print(f"WARNING: {e}")
        print("Service starting without models - endpoints may fail")
    
    yield
    
    # Shutdown: Clean up
    print(f"Shutting down {settings.SERVICE_NAME}...")
    ModelLoader.clear()


app = FastAPI(
    title="FaceLogix Face Recognition Service",
    description=(
        "Face detection, embedding generation, and liveness detection API. "
        "Provides endpoints for processing face images using RetinaFace "
        "detection and ArcFace embedding generation."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix="/api/v1")


@app.get("/health", tags=["Health"])
async def health_check() -> dict:
    """
    Health check endpoint.
    
    Returns service health status and model loading state.
    """
    models_loaded = (
        "detector" in ModelLoader._instances and
        "embedder" in ModelLoader._instances
    )
    
    return {
        "status": "healthy",
        "service": settings.SERVICE_NAME,
        "models_loaded": models_loaded
    }


@app.get("/", tags=["Root"])
async def root() -> dict:
    """
    Root endpoint with service information.
    """
    return {
        "service": settings.SERVICE_NAME,
        "version": "1.0.0",
        "docs": "/api/docs"
    }
