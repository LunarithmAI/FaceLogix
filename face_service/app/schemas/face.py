"""
Pydantic schemas for face recognition API requests and responses.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class BoundingBox(BaseModel):
    """
    Face bounding box with confidence score.
    
    Attributes:
        x1: Left edge x-coordinate
        y1: Top edge y-coordinate
        x2: Right edge x-coordinate
        y2: Bottom edge y-coordinate
        confidence: Detection confidence score (0-1)
    """
    x1: int = Field(..., description="Left edge x-coordinate")
    y1: int = Field(..., description="Top edge y-coordinate")
    x2: int = Field(..., description="Right edge x-coordinate")
    y2: int = Field(..., description="Bottom edge y-coordinate")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detection confidence")


class DetectionResponse(BaseModel):
    """
    Response from face detection endpoint.
    
    Attributes:
        faces: List of detected face bounding boxes
        count: Number of faces detected
    """
    faces: List[BoundingBox] = Field(
        default_factory=list,
        description="List of detected face bounding boxes"
    )
    count: int = Field(..., ge=0, description="Number of faces detected")


class EmbeddingResponse(BaseModel):
    """
    Response from face embedding generation endpoint.
    
    Attributes:
        embedding: 512-dimensional L2-normalized embedding vector
        quality_score: Overall quality score of the face image (0-1)
        bbox: Bounding box of the detected face (optional)
    """
    embedding: List[float] = Field(
        ...,
        min_length=512,
        max_length=512,
        description="512-dimensional face embedding vector"
    )
    quality_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Overall quality score of the face image"
    )
    bbox: Optional[BoundingBox] = Field(
        None,
        description="Bounding box of the detected face"
    )


class LivenessResponse(BaseModel):
    """
    Response from liveness detection endpoint.
    
    Attributes:
        is_live: Whether the face is from a live person
        confidence: Confidence score for the liveness determination (0-1)
        reason: Human-readable explanation of the result
    """
    is_live: bool = Field(..., description="Whether the face is from a live person")
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Liveness confidence score"
    )
    reason: str = Field(..., description="Explanation of the liveness result")
