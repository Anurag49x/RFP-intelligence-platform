"""Configuration management for RFP Intelligence Platform."""

from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Core Application
    app_env: str = "development"
    log_level: str = "INFO"

    # LLM & Vision/OCR Settings (Groq)
    groq_api_key: Optional[str] = None
    groq_model: Optional[str] = "qwen/qwen3.8-27b"
    groq_ocr_model: Optional[str] = "qwen/qwen3.8-27b"
    ocr_cache_dir: str = "outputs/ocr_cache"

    # Embeddings & Reranking (Phase 3 & 5)
    jina_api_key: Optional[str] = None
    jina_api_url: str = "https://api.jina.ai/v1"
    jina_embedding_model: Optional[str] = "jina-embeddings-v3"
    jina_reranker_model: Optional[str] = "jina-reranker-v3.5"
    rerank_top_k: int = 5
    dense_top_k: int = 20
    bm25_top_k: int = 20

    # Vector Database (Phase 3+)
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: Optional[str] = None

    # Observability (Phase 16)
    langsmith_api_key: Optional[str] = None
    langsmith_tracing: bool = False
    langsmith_project: str = "rfp-intelligence"


@lru_cache()
def get_settings() -> Settings:
    """Return a cached instance of application settings."""
    return Settings()
