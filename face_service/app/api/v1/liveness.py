"""
Liveness Detection Endpoint.

Provides API endpoint for verifying face liveness using two-frame analysis.
"""

import cv2
import numpy as np
from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.pipeline.liveness import LivenessDetector
from app.schemas.face import LivenessResponse

router = APIRouter()

# Initialize liveness detector
liveness_detector = LivenessDetector()


@router.post("/liveness", response_model=LivenessResponse)
async def check_liveness(
    frame1: UploadFile = File(..., description="First frame (JPEG/PNG)"),
    frame2: UploadFile = File(..., description="Second frame (~500ms later)")
) -> LivenessResponse:
    """
    Check if face is from a live person using two frames.
    
    Analyzes natural micro-movements between two consecutive frames
    to distinguish live faces from presentation attacks (photos/videos).
    
    Frames should be captured approximately 500ms apart for optimal
    detection of natural micro-movements.
    
    Args:
        frame1: First captured frame
        frame2: Second captured frame (~500ms after first)
        
    Returns:
        LivenessResponse with is_live, confidence, and reason
        
    Raises:
        HTTPException 400: If either frame format is invalid
    """
    # Read and decode first frame
    contents1 = await frame1.read()
    nparr1 = np.frombuffer(contents1, np.uint8)
    img1 = cv2.imdecode(nparr1, cv2.IMREAD_COLOR)
    
    if img1 is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid format for first frame. Please provide a valid JPEG or PNG image."
        )
    
    # Read and decode second frame
    contents2 = await frame2.read()
    nparr2 = np.frombuffer(contents2, np.uint8)
    img2 = cv2.imdecode(nparr2, cv2.IMREAD_COLOR)
    
    if img2 is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid format for second frame. Please provide a valid JPEG or PNG image."
        )
    
    # Check liveness
    result = liveness_detector.check_liveness(img1, img2)
    
    return LivenessResponse(
        is_live=result.is_live,
        confidence=result.confidence,
        reason=result.reason
    )
