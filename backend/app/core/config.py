# backend/app/core/config.py
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # AWS Configuration
    aws_region: str = "us-east-1"
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    
    # Database Configuration
    database_url: str = "postgresql://app_user:secure_password@postgres:5432/resume_screening"
    
    # Redis Configuration
    redis_url: str = "redis://redis:6379"
    
    # ChromaDB Configuration
    chroma_db_path: str = "/app/data/chroma_db"
    
    # Application Configuration
    app_name: str = "Smart Resume Screening System"
    debug: bool = False
    log_level: str = "INFO"
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    workers: int = 4
    
    # Performance Settings
    chunk_size: int = 1000
    chunk_overlap: int = 200
    embedding_batch_size: int = 5
    cache_ttl: int = 3600
    
    class Config:
        env_file = ".env"

settings = Settings()
