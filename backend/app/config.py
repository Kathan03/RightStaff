"""
Configuration management for RightStaff AI Backend.
Loads settings from environment variables with validation.
"""

from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from typing import Optional
from urllib.parse import quote_plus


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Environment
    debug: bool = Field(default=False, env="DEBUG")
    env: str = Field(default="development", env="ENV")

    # PostgreSQL
    postgres_host: str = Field(default="localhost", env="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, env="POSTGRES_PORT")
    postgres_db: str = Field(default="rightstaff", env="POSTGRES_DB")
    postgres_user: str = Field(default="right_staff", env="POSTGRES_USER")
    postgres_password: str = Field(default="dev_password_123", env="POSTGRES_PASSWORD")

    # Qdrant
    qdrant_host: str = Field(default="localhost", env="QDRANT_HOST")
    qdrant_port: int = Field(default=6333, env="QDRANT_PORT")
    qdrant_collection: str = Field(default="candidates_v1", env="QDRANT_COLLECTION")

    # Redis
    redis_host: str = Field(default="localhost", env="REDIS_HOST")
    redis_port: int = Field(default=6379, env="REDIS_PORT")
    redis_password: str = Field(default="dev_redis_123", env="REDIS_PASSWORD")
    redis_db: int = Field(default=0, env="REDIS_DB")

    # MinIO
    minio_endpoint: str = Field(default="localhost:9000", env="MINIO_ENDPOINT")
    minio_access_key: str = Field(default="minioadmin", env="MINIO_ACCESS_KEY")
    minio_secret_key: str = Field(default="minioadmin123", env="MINIO_SECRET_KEY")
    minio_bucket: str = Field(default="rightstaff-resumes", env="MINIO_BUCKET")
    minio_use_ssl: bool = Field(default=False, env="MINIO_USE_SSL")

    # AI Models
    embedding_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        env="EMBEDDING_MODEL"
    )
    embedding_dim: int = Field(default=384, env="EMBEDDING_DIM")
    
    # Text Processing
    chunk_size: int = Field(default=400, env="CHUNK_SIZE", ge=50, le=2000)
    chunk_overlap: int = Field(default=50, env="CHUNK_OVERLAP", ge=0, le=500)

    # Cross-Encoder for Re-ranking (MVP - Days 9-10)
    reranker_model: str = Field(
        default="cross-encoder/ms-marco-MiniLM-L-6-v2",
        env="RERANKER_MODEL"
    )

    # OpenAI (optional, for production)
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")

    # API Settings
    api_rate_limit: int = Field(default=100, env="API_RATE_LIMIT")
    max_file_size_mb: int = Field(default=5, env="MAX_FILE_SIZE_MB")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    @field_validator("chunk_overlap")
    @classmethod
    def validate_chunk_overlap(cls, v, info):
        """Ensure chunk_overlap is less than chunk_size."""
        chunk_size = info.data.get("chunk_size", 400)
        if v >= chunk_size:
            raise ValueError(f"chunk_overlap ({v}) must be less than chunk_size ({chunk_size})")
        return v

    @property
    def database_url(self) -> str:
        """Get PostgreSQL connection URL (synchronous).

        URL-encodes username and password to handle special characters like @, :, /, etc.
        """
        encoded_user = quote_plus(self.postgres_user)
        encoded_password = quote_plus(self.postgres_password)
        return (
            f"postgresql://{encoded_user}:{encoded_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def async_database_url(self) -> str:
        """Get async PostgreSQL connection URL (for asyncpg).

        Uses postgresql+asyncpg:// driver for async operations.
        """
        encoded_user = quote_plus(self.postgres_user)
        encoded_password = quote_plus(self.postgres_password)
        return (
            f"postgresql+asyncpg://{encoded_user}:{encoded_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def redis_url(self) -> str:
        """Get Redis connection URL.
        
        URL-encodes password to handle special characters like @, :, /, etc.
        """
        encoded_password = quote_plus(self.redis_password)
        return f"redis://:{encoded_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"


# Global settings instance
settings = Settings()
