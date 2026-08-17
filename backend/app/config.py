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
        "postgresql://knowledgehub:knowledgehub_dev_password@localhost:5432/knowledgehub"
    )

    # Timeout (seconds) when acquiring a database connection from the pool
    database_pool_min_size: int = 1
    database_pool_max_size: int = 5


# Single shared instance — import this wherever settings are needed
settings = Settings()
