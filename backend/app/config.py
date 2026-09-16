import os
from enum import Enum
from pydantic_settings import BaseSettings
from pydantic import Field


class LLMProvider(str, Enum):
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"


class Settings(BaseSettings):
    # App
    APP_NAME: str = "The Lenny Growth Assistant"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # LLM Provider Toggle
    LLM_PROVIDER: LLMProvider = LLMProvider.ANTHROPIC

    # Anthropic
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-haiku-4-5-20251001"

    # Ollama
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2"
    OLLAMA_EMBED_MODEL: str = "nomic-embed-text"

    # Database — SQLite (local dev) or PostgreSQL (production/Docker)
    # Local: sqlite+aiosqlite:///./lenny.db
    # Docker: postgresql+asyncpg://lenny:lenny_pass@postgres:5432/lenny_db
    DATABASE_URL: str = "sqlite+aiosqlite:///./lenny.db"

    # ChromaDB
    CHROMA_PERSIST_DIR: str = "./data/chroma"
    CHROMA_COLLECTION: str = "lenny_transcripts"

    # RAG
    RAG_CHUNK_SIZE: int = 800
    RAG_CHUNK_OVERLAP: int = 100
    RAG_TOP_K: int = 5

    # CORS — add Render URLs via env: CORS_ORIGINS='["https://xxx.onrender.com"]'
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "https://lenny-growth-frontend.onrender.com",
    ]

    # Transcript data
    TRANSCRIPTS_DIR: str = "./data/transcripts"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
