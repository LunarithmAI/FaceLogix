from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    SERVICE_NAME: str = "face-recognition-service"
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    MODELS_DIR: Path = Path("models")

    DETECTION_THRESHOLD: float = Field(default=0.5, ge=0.0, le=1.0)
    MIN_FACE_SIZE: int = Field(default=50, ge=1, le=4096)
    MAX_FACES: int = Field(default=10, ge=2, le=100)
    MIN_QUALITY_SCORE: float = Field(default=0.3, ge=0.0, le=1.0)
    ONNX_PROVIDERS: list[str] = Field(default_factory=lambda: ["CPUExecutionProvider"])

    MAX_UPLOAD_BYTES: int = Field(default=10 * 1024 * 1024, ge=1)
    MAX_IMAGE_DIMENSION: int = Field(default=4096, ge=1, le=16384)
    MAX_IMAGE_PIXELS: int = Field(default=16_777_216, ge=1)
    MAX_CONCURRENT_INFERENCES: int = Field(default=1, ge=1, le=32)
    ORT_INTRA_OP_THREADS: int = Field(default=2, ge=1, le=64)
    ORT_INTER_OP_THREADS: int = Field(default=1, ge=1, le=64)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
