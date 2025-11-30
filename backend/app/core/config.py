from pydantic_settings import BaseSettings
from typing import List
from functools import lru_cache

class Settings(BaseSettings):
    # App
    APP_NAME: str = "FaceLogix"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://user:pass@localhost:5432/facelogix"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # JWT
    JWT_SECRET_KEY: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Device tokens
    DEVICE_TOKEN_SECRET: str = "device-secret-key-change-in-production"
    DEVICE_TOKEN_EXPIRE_DAYS: int = 365
    
    # Face Service
    FACE_SERVICE_URL: str = "http://face-service:8001"
    FACE_SERVICE_TIMEOUT: int = 10
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]
    
    # Recognition
    DEFAULT_RECOGNITION_THRESHOLD: float = 0.75
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"

@lru_cache
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
