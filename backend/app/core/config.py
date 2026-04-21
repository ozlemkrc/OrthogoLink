"""
Application configuration loaded from environment variables.
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Curriculum Orthogonality Checker"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@db:5432/orthogonality"
    DATABASE_URL_SYNC: str = "postgresql://postgres:postgres@db:5432/orthogonality"

    # CORS
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:80,http://localhost"

    # AI Model
    MODEL_NAME: str = "all-MiniLM-L6-v2"
    SIMILARITY_THRESHOLD: float = 0.70

    # FAISS index path
    FAISS_INDEX_PATH: str = "/app/data/faiss_index"

    # Auth
    SECRET_KEY: str = "orthogolink-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
