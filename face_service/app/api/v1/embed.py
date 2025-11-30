"""
Face Embedding Generation Endpoint.

Provides API endpoint for generating face embeddings from images.
"""

import cv2
import numpy as np
from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.core.config import settings
from app.pipeline.aligner import FaceAligner
from app.pipeline.detector import FaceDetector
from app.pipeline.embedder import FaceEmbedder
from app.pipeline.quality import QualityAssessor
from app.schemas.face import BoundingBox, EmbeddingResponse

router = APIRouter()

# Initialize pipeline components
detector = FaceDetector()
aligner = FaceAligner()
embedder = FaceEmbedder()
quality_assessor = QualityAssessor()


@router.post("/embed", response_model=EmbeddingResponse)
async def generate_embedding(
    image: UploadFile = File(..., description="Face image (JPEG/PNG)")
) -> EmbeddingResponse:
    """
    Generate face embedding from an image.
    
    Detects the primary face in the image, assesses quality,
    aligns the face, and generates a 512-dimensional normalized
    embedding vector.
    
    Args:
        image: Uploaded image file containing a face
        
    Returns:
        EmbeddingResponse with embedding vector, quality score, and bbox
        
    Raises:
        HTTPException 400: If image is invalid, no face detected,
            or quality is too low
    """
    # Read and decode image
    contents = await image.read()
    nparr = np.frombuffer(contents, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    if img is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image format. Please provide a valid JPEG or PNG image."
        )
    
    # Detect faces
    faces = detector.detect(img)
    
    if not faces:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No face detected in image. Please provide an image with a visible face."
        )
    
    # Use the face with highest confidence
    face = faces[0]
    
    # Assess image quality
    quality = quality_assessor.assess(img, face)
    
    if quality.overall < settings.MIN_QUALITY_SCORE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Face quality too low ({quality.overall:.2f}). "
                "Please provide a clearer image with good lighting and focus."
            )
        )
    
    # Align face for embedding generation
    aligned = aligner.align(img, face.landmarks)
    
    # Generate embedding
    embedding = embedder.generate(aligned)
    
    return EmbeddingResponse(
        embedding=embedding.tolist(),
        quality_score=quality.overall,
        bbox=BoundingBox(
            x1=face.bbox[0],
            y1=face.bbox[1],
            x2=face.bbox[2],
            y2=face.bbox[3],
            confidence=face.confidence
        )
    )
