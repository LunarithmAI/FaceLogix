from dataclasses import dataclass

import httpx
from fastapi import HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, ValidationError

from app.core.images import image_media_type

STABLE_FACE_CODES = {
    "INVALID_IMAGE",
    "NO_FACE",
    "MULTIPLE_FACES",
    "LOW_QUALITY",
    "IMAGE_TOO_LARGE",
    "UNSUPPORTED_MEDIA_TYPE",
    "INFERENCE_BUSY",
    "MODEL_UNAVAILABLE",
    "INFERENCE_FAILED",
}


class FaceBoundingBox(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    x1: int
    y1: int
    x2: int
    y2: int
    confidence: float = Field(ge=0.0, le=1.0)


class FaceAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    embedding: list[FiniteFloat] = Field(min_length=512, max_length=512)
    quality_score: float = Field(ge=0.0, le=1.0)
    bbox: FaceBoundingBox
    pad_live_score: float = Field(ge=0.0, le=1.0)


@dataclass(slots=True)
class FaceServiceError(Exception):
    status_code: int
    code: str
    message: str


def _service_error(response: httpx.Response) -> FaceServiceError:
    code = "INFERENCE_FAILED"
    message = "Face analysis failed"
    try:
        detail = response.json().get("detail")
        if isinstance(detail, dict):
            response_code = detail.get("code")
            response_message = detail.get("message")
            if isinstance(response_code, str) and response_code in STABLE_FACE_CODES:
                code = response_code
            if isinstance(response_message, str) and response_message:
                message = response_message
    except (ValueError, AttributeError):
        pass
    return FaceServiceError(response.status_code, code, message)


class FaceServiceClient:
    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def analyze(self, image_bytes: bytes) -> FaceAnalysis:
        media_type = image_media_type(image_bytes)
        if media_type is None:
            raise FaceServiceError(
                415, "UNSUPPORTED_MEDIA_TYPE", "Only JPEG and PNG images are supported"
            )
        try:
            response = await self._client.post(
                "/api/v1/analyze",
                files={"image": ("face", image_bytes, media_type)},
            )
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            raise FaceServiceError(
                503, "MODEL_UNAVAILABLE", "Face analysis service is unavailable"
            ) from exc
        if response.status_code != 200:
            raise _service_error(response)
        try:
            return FaceAnalysis.model_validate(response.json())
        except (ValueError, ValidationError) as exc:
            raise FaceServiceError(
                500, "INFERENCE_FAILED", "Face analysis returned an invalid response"
            ) from exc

    async def ready(self) -> bool:
        try:
            response = await self._client.get("/health/ready")
        except httpx.HTTPError:
            return False
        return response.status_code == 200


def get_face_client(request: Request) -> FaceServiceClient:
    client = getattr(request.app.state, "face_client", None)
    if not isinstance(client, FaceServiceClient):
        raise HTTPException(
            status_code=503,
            detail={"code": "MODEL_UNAVAILABLE", "message": "Face analysis service is unavailable"},
        )
    return client
