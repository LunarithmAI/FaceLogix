from functools import partial
from typing import Annotated

from fastapi import APIRouter, Depends, File, Request, UploadFile

from app.api.deps import get_pipeline, run_inference
from app.core.images import read_upload
from app.pipeline.face import FacePipeline
from app.schemas.face import BoundingBox, FaceAnalysisResponse

router = APIRouter()


@router.post("/analyze", response_model=FaceAnalysisResponse)
async def analyze_face(
    request: Request,
    image: Annotated[UploadFile, File(description="Face image (JPEG/PNG)")],
    pipeline: Annotated[FacePipeline, Depends(get_pipeline)],
) -> FaceAnalysisResponse:
    data, content_type = await read_upload(image, pipeline.settings)
    analysis = await run_inference(
        request,
        partial(pipeline.analyze_bytes, data, content_type),
    )
    face = analysis.face
    return FaceAnalysisResponse(
        embedding=analysis.embedding.tolist(),
        quality_score=analysis.quality_score,
        bbox=BoundingBox(
            x1=face.bbox[0],
            y1=face.bbox[1],
            x2=face.bbox[2],
            y2=face.bbox[3],
            confidence=face.confidence,
        ),
        pad_live_score=analysis.pad_live_score,
    )
