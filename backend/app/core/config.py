"""Application settings, loaded from environment variables and the project's .env file."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/core/config.py -> project root is three levels above this folder
ROOT_DIR = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",  # ignore variables used only by Docker (POSTGRES_USER, ...)
    )

    environment: str = "development"

    # Required: the app refuses to start without these.
    database_url: str
    redis_url: str
    secret_key: str

    session_cookie_name: str = "heimdall_session"
    cors_origins: str = "http://localhost:3000"
    frontend_url: str = "http://localhost:3000"

    # Local LLM (Ollama)
    llm_base_url: str = "http://localhost:11434"
    llm_model_name: str = "qwen3:4b"
    llm_api_key: str = ""
    llm_think: bool = False
    llm_num_ctx: int = 4096

    # Embeddings and reranker
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_dim: int = 384
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    # Retrieval (starting values; tune with the evaluation set)
    retrieval_top_k: int = 20
    rerank_top_k: int = 5
    similarity_threshold: float = 0.30

    # Documents
    storage_path: str = "./storage"
    max_upload_mb: int = 10
    allowed_file_types: str = "pdf,txt,md"
    chunk_size_tokens: int = 500
    chunk_overlap_tokens: int = 75

    # Limits and retention
    max_active_keys_per_tenant: int = 5
    rate_limit_per_minute: int = 60
    monthly_query_quota: int = 1000
    trace_retention_days: int = 30

    # Test database (optional, for integration tests)
    test_database_url: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
