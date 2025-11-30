"""
Face Detection Endpoint.

Provides API endpoint for detecting faces in images.
"""

import cv2
import numpy as np
from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.pipeline.detector import FaceDetector
from app.schemas.face import BoundingBox, DetectionResponse

router = APIRouter()

# Initialize detector
detector = FaceDetector()


@router.post("/detect", response_model=DetectionResponse)
async def detect_faces(
    image: UploadFile = File(..., description="Image to analyze (JPEG/PNG)")
) -> DetectionResponse:
    """
    Detect all faces in an image.
    
    Returns bounding boxes with confidence scores for each detected face,
    sorted by confidence (highest first).
    
    Args:
        image: Uploaded image file to analyze
        
    Returns:
        DetectionResponse with list of face bounding boxes and count
        
    Raises:
        HTTPException 400: If image format is invalid
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
    
    # Convert to response format
    return DetectionResponse(
        faces=[
            BoundingBox(
                x1=f.bbox[0],
                y1=f.bbox[1],
                x2=f.bbox[2],
                y2=f.bbox[3],
                confidence=f.confidence
            )
            for f in faces
        ],
        count=len(faces)
    )
