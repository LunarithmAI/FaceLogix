from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",
    )

    ENVIRONMENT: Literal["development", "test", "production"] = "development"
    APP_NAME: str = "FaceLogix"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    DATABASE_URL: str = "postgresql+asyncpg://user:pass@localhost:5432/facelogix"
    DATABASE_POOL_SIZE: int = Field(default=20, gt=0)
    DATABASE_MAX_OVERFLOW: int = Field(default=10, ge=0)

    JWT_SECRET_KEY: str = Field(min_length=32)
    JWT_ALGORITHM: Literal["HS256"] = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, gt=0)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, gt=0)

    DEVICE_TOKEN_SECRET: str = Field(min_length=32)
    DEVICE_TOKEN_EXPIRE_DAYS: int = Field(default=365, gt=0)

    FACE_SERVICE_URL: str = "http://face-service:8001"
    FACE_SERVICE_TIMEOUT: float = Field(default=10.0, gt=0)

    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    @field_validator("JWT_SECRET_KEY", "DEVICE_TOKEN_SECRET")
    @classmethod
    def reject_blank_secrets(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("secret must not be blank")
        return value

    @model_validator(mode="after")
    def reject_production_templates(self) -> "Settings":
        if self.ENVIRONMENT != "production":
            return self
        template_values = {
            "your-secret-key-change-in-production",
            "device-secret-key-change-in-production",
            "change-me",
            "changeme",
        }
        if self.JWT_SECRET_KEY.lower() in template_values:
            raise ValueError("JWT_SECRET_KEY uses a template value")
        if self.DEVICE_TOKEN_SECRET.lower() in template_values:
            raise ValueError("DEVICE_TOKEN_SECRET uses a template value")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
