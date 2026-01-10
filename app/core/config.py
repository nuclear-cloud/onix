import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"  # Ignore extra env vars like ALLOWED_ORIGINS
    )
    
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    PRISMA_DATABASE_URL: str = os.getenv("PRISMA_DATABASE_URL", "")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "qwen2.5:3b")
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")


settings = Settings()
