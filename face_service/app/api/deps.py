import logging
from collections.abc import Callable
from typing import TypeVar, cast

import anyio
from fastapi import Request

from app.core.errors import FaceServiceError
from app.pipeline.face import FacePipeline

T = TypeVar("T")
logger = logging.getLogger(__name__)


def get_pipeline(request: Request) -> FacePipeline:
    pipeline = getattr(request.app.state, "face_pipeline", None)
    if not isinstance(pipeline, FacePipeline):
        raise FaceServiceError("MODEL_UNAVAILABLE", "Face models are unavailable", 503)
    return pipeline


async def run_inference(request: Request, operation: Callable[[], T]) -> T:
    limiter = cast(anyio.CapacityLimiter, request.app.state.inference_limiter)
    try:
        limiter.acquire_nowait()
    except anyio.WouldBlock as exc:
        raise FaceServiceError("INFERENCE_BUSY", "Inference capacity is busy", 429) from exc
    try:
        return await anyio.to_thread.run_sync(operation)
    except FaceServiceError:
        raise
    except Exception as exc:
        logger.exception("Face inference failed")
        raise FaceServiceError(
            "INFERENCE_FAILED",
            "Face inference failed",
            500,
        ) from exc
    finally:
        limiter.release()
