from pydantic_settings import BaseSettings
from functools import lru_cache
import os

# Load secrets from Docker secrets (/run/secrets) or other sources before
# pydantic loads settings so env vars are available.
from .secrets import load_docker_secrets, load_local_secret_file, try_load_aws_secret


# Names to check for docker secrets. These map to env var names used by
# the application and by Pydantic's `BaseSettings`.
_SECRET_NAMES = [
    "OPENAI_API_KEY",
    "GOOGLE_API_KEY",
    "API_KEY",
    "DATABASE_URL",
    "REDIS_URL",
]

# Try to load docker secrets (if running in Docker with secrets mounted).
load_docker_secrets(_SECRET_NAMES)

# Also support a developer-friendly local file at `backend/.secrets/<name>`
# (optional) so users can place secrets there for local testing without
# committing them to `.env`.
secrets_dir = os.path.join(os.path.dirname(__file__), "..", ".secrets")
for name in _SECRET_NAMES:
    local_path = os.path.join(secrets_dir, name)
    load_local_secret_file(local_path, name)

# Optionally attempt to read from AWS Secrets Manager when configured.
# This will silently no-op when boto3 or creds are not available.
try_load_aws_secret("video-rag/openai", "OPENAI_API_KEY")
try_load_aws_secret("video-rag/google", "GOOGLE_API_KEY")


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
