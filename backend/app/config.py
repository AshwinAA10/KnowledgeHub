"""
KnowledgeHub — Application Configuration
=========================================
All configuration is loaded from environment variables (or a .env file).
No hardcoded values. Add new settings here as the project grows.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Priority order (highest to lowest):
      1. Actual environment variables
      2. Variables in the .env file (if present)
      3. Default values defined below
    """

    model_config = SettingsConfigDict(
        # Look for a .env file in the backend/ directory when running locally
        env_file=".env",
        env_file_encoding="utf-8",
        # Ignore extra fields that might appear in .env (forward-compatible)
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────────────────
    app_env: str = "development"
    app_debug: bool = True

    # ── Database ─────────────────────────────────────────────────────────────
    database_url: str = (
        "postgresql://knowledgehub:knowledgehub_dev_password@localhost:5433/knowledgehub"
    )

    # Timeout (seconds) when acquiring a database connection from the pool
    database_pool_min_size: int = 1
    database_pool_max_size: int = 5

    # ── Document Ingestion & Storage ─────────────────────────────────────────
    # Local directory to store uploaded PDF files
    upload_dir: str = "uploads"
    # Max allowed upload file size (20 MB default)
    max_upload_size_bytes: int = 20 * 1024 * 1024

    # ── Chunking ─────────────────────────────────────────────────────────────
    # Deterministic chunking defaults
    chunk_size: int = 500
    chunk_overlap: int = 50

    # ── Embeddings ───────────────────────────────────────────────────────────
    # Embedding model name and expected vector dimension
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_dimensions: int = 384
    embedding_batch_size: int = 32

    # ── LLM (OpenAI Responses API) ───────────────────────────────────────────
    openai_api_key: str = ""
    openai_model: str = "gpt-5.5"
    openai_request_timeout: float = 60.0
    openai_max_retries: int = 2


# Single shared instance — import this wherever settings are needed
settings = Settings()
