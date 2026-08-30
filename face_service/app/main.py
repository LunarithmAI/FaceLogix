import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import anyio
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.errors import FaceServiceError
from app.models.loader import FaceModels
from app.pipeline.face import FacePipeline

logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.ready = False
    app.state.inference_limiter = anyio.CapacityLimiter(settings.MAX_CONCURRENT_INFERENCES)
    models = await anyio.to_thread.run_sync(FaceModels.load, settings)
    app.state.face_pipeline = FacePipeline(models, settings)
    app.state.ready = True
    try:
        yield
    finally:
        app.state.ready = False
        app.state.face_pipeline = None


def create_app() -> FastAPI:
    application = FastAPI(
        title=settings.SERVICE_NAME,
        description="Internal face analysis service",
        version="1.0.0",
        lifespan=lifespan,
    )
    application.state.ready = False
    application.include_router(api_router, prefix="/api/v1")

    @application.exception_handler(FaceServiceError)
    async def face_error_handler(
        _request: Request,
        exc: FaceServiceError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": {"code": exc.code, "message": exc.message}},
        )

    @application.get("/health/live", tags=["Health"])
    async def live() -> dict[str, str]:
        return {"status": "alive"}

    @application.get("/health/ready", tags=["Health"])
    async def ready(request: Request) -> JSONResponse:
        if not request.app.state.ready:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "detail": {
                        "code": "MODEL_UNAVAILABLE",
                        "message": "Face models are unavailable",
                    }
                },
            )
        return JSONResponse(content={"status": "ready"})

    return application


app = create_app()
