"""
Configuration settings for the Face Recognition Service.

Uses pydantic-settings for environment variable management with sensible defaults.
"""

from functools import lru_cache
from pathlib import Path
from typing import List, Tuple

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    Attributes:
        SERVICE_NAME: Name of the service for identification
        DEBUG: Enable debug mode
        LOG_LEVEL: Logging level
        MODELS_DIR: Directory containing ONNX model files
        DETECTOR_MODEL: Filename of the face detector model
        EMBEDDER_MODEL: Filename of the face embedder model
        DETECTION_THRESHOLD: Minimum confidence for face detection
        MIN_FACE_SIZE: Minimum face size in pixels
        MAX_FACES: Maximum number of faces to detect
        EMBEDDING_SIZE: Dimension of face embeddings
        INPUT_SIZE: Input size for face alignment (width, height)
        LIVENESS_MOVEMENT_THRESHOLD: Movement threshold for liveness detection
        LIVENESS_MIN_FRAMES: Minimum frames required for liveness check
        MIN_QUALITY_SCORE: Minimum quality score for embedding generation
        ONNX_PROVIDERS: List of ONNX execution providers
    """
    
    # Service configuration
    SERVICE_NAME: str = "face-recognition-service"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    
    # Model paths
    MODELS_DIR: Path = Path("models")
    DETECTOR_MODEL: str = "det_10g.onnx"
    EMBEDDER_MODEL: str = "w600k_r50.onnx"
    
    # Detection settings
    DETECTION_THRESHOLD: float = 0.5
    MIN_FACE_SIZE: int = 50
    MAX_FACES: int = 10
    
    # Face detection/recognition thresholds (from env)
    FACE_DETECTION_THRESHOLD: float = 0.5
    FACE_RECOGNITION_THRESHOLD: float = 0.75
    MAX_FACES_PER_IMAGE: int = 10
    
    # Embedding settings
    EMBEDDING_SIZE: int = 512
    INPUT_SIZE: Tuple[int, int] = (112, 112)
    
    # Liveness settings
    LIVENESS_MOVEMENT_THRESHOLD: float = 0.02
    LIVENESS_MIN_FRAMES: int = 2
    
    # Quality settings
    MIN_QUALITY_SCORE: float = 0.3
    
    # Performance / ONNX runtime
    ONNX_PROVIDERS: List[str] = ["CPUExecutionProvider"]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.
    
    Returns:
        Settings: Application settings singleton
    """
    return Settings()


settings = get_settings()
