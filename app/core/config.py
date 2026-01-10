import os
from typing import Optional
from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"  # Ignore extra env vars like ALLOWED_ORIGINS
    )
    
    # Database (required)
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    PRISMA_DATABASE_URL: str = os.getenv("PRISMA_DATABASE_URL", "")
    
    # API Keys (secrets - won't be logged)
    GROQ_API_KEY: SecretStr = SecretStr(os.getenv("GROQ_API_KEY", ""))
    
    # ML/AI Settings
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "qwen2.5:3b")
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
    
    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    
    # Cache TTL (seconds)
    STATS_CACHE_TTL: int = int(os.getenv("STATS_CACHE_TTL", "300"))  # 5 minutes
    
    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        if v and not v.startswith(("postgresql://", "postgres://")):
            raise ValueError("DATABASE_URL must be a PostgreSQL connection string")
        return v


settings = Settings()
