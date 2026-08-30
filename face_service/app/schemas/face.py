from pydantic import BaseModel, Field, FiniteFloat


class BoundingBox(BaseModel):
    x1: int
    y1: int
    x2: int
    y2: int
    confidence: float = Field(ge=0.0, le=1.0)


class FaceAnalysisResponse(BaseModel):
    embedding: list[FiniteFloat] = Field(min_length=512, max_length=512)
    quality_score: float = Field(ge=0.0, le=1.0)
    bbox: BoundingBox
    pad_live_score: float = Field(ge=0.0, le=1.0)
