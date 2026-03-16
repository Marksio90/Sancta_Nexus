"""Application configuration using pydantic-settings.

All settings are loaded from environment variables with fallback to a .env file.
Sensitive values (API keys, passwords) have no defaults and must be provided.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for the Sancta Nexus platform.

    Groups:
        - Application metadata
        - Database connections (Postgres, Redis, Neo4j, Qdrant)
        - External API keys (OpenAI, Anthropic, ElevenLabs)
        - Authentication / JWT
        - Domain-specific thresholds
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────────────
    APP_NAME: str = "Sancta Nexus"
    VERSION: str = "1.0.0"
    DEBUG: bool = False

    # ── Relational database (PostgreSQL via asyncpg) ─────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/sancta_nexus"

    # ── Redis ────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── Neo4j (spiritual-knowledge graph) ────────────────────────────────
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "neo4j"

    # ── Qdrant (vector store for embeddings) ─────────────────────────────
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_API_KEY: str | None = None

    # ── External AI APIs ─────────────────────────────────────────────────
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    ELEVENLABS_API_KEY: str = ""

    # ── Authentication / JWT ─────────────────────────────────────────────
    SECRET_KEY: str = "CHANGE-ME-IN-PRODUCTION"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # ── Domain-specific settings ─────────────────────────────────────────
    THEOLOGY_VALIDATION_THRESHOLD: float = 0.85
    EMOTION_DIMENSIONS: int = 36


settings = Settings()
