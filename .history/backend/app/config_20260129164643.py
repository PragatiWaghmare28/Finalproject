from pydantic_settings import BaseSettings
from functools import lru_cache
import os


class Settings(BaseSettings):
    # App
    app_name: str = "Video-RAG API"
    debug: bool = True
    
    # Database
    database_url: str = "sqlite:///./videorag.db"
    
    # Vector DB
    chroma_persist_dir: str = "./chroma_db"
    
    # AI Services
    openai_api_key: str = ""
    google_api_key: str = ""
    
    # Which LLM to use: "openai" or "google"
    llm_provider: str = "google"

    # Simple API key for protecting sensitive endpoints (set in production)
    api_key: str = ""
    
    # File Storage
    upload_dir: str = "./uploads"
    max_file_size: int = 500 * 1024 * 1024  # 500MB
    
    # Redis
    redis_url: str = "redis://localhost:6379"
    
    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


# Create upload directory if it doesn't exist
settings = get_settings()
os.makedirs(settings.upload_dir, exist_ok=True)
os.makedirs(settings.chroma_persist_dir, exist_ok=True)
