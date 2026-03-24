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

    # ── ElevenLabs sacred voice IDs (optional — configure for premium TTS) ──
    # Leave empty to use OpenAI TTS as primary provider.
    ELEVENLABS_VOICE_NARRATOR_MALE: str = ""    # e.g. "pNInz6obpgDQGcFmaJgB"
    ELEVENLABS_VOICE_NARRATOR_FEMALE: str = ""  # e.g. "EXAVITQu4vr4xnSDxMaL"
    ELEVENLABS_VOICE_CONTEMPLATIVE: str = ""    # e.g. "VR6AewLTigWG4xSOukaG"
    ELEVENLABS_VOICE_SACRED: str = ""           # e.g. "ErXwobaYiN019PkySvjV"

    # ── VAPID (Web Push Notifications) ───────────────────────────────────────
    # Generate keys: python -m py_vapid --gen-key
    VAPID_PRIVATE_KEY: str = ""
    VAPID_PUBLIC_KEY: str = ""
    VAPID_CLAIMS_EMAIL: str = "mailto:admin@sanctanexus.org"

    # ── LLM Configuration ─────────────────────────────────────────────────
    LLM_PROVIDER: str = "openai"  # "openai" or "anthropic"
    LLM_FALLBACK_PROVIDER: str = "anthropic"  # secondary provider

    # Primary models (theology, exegesis, spiritual direction)
    LLM_PRIMARY_MODEL: str = "gpt-4o"
    LLM_PRIMARY_ANTHROPIC_MODEL: str = "claude-sonnet-4-20250514"

    # Fast models (emotion detection, classification, quick checks)
    LLM_FAST_MODEL: str = "gpt-4o-mini"
    LLM_FAST_ANTHROPIC_MODEL: str = "claude-sonnet-4-20250514"

    # Creative models (prayer generation, reflections)
    LLM_CREATIVE_MODEL: str = "gpt-4o"
    LLM_CREATIVE_ANTHROPIC_MODEL: str = "claude-sonnet-4-20250514"

    # ── Authentication / JWT ─────────────────────────────────────────────
    SECRET_KEY: str = "CHANGE-ME-IN-PRODUCTION"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # ── Domain-specific settings ─────────────────────────────────────────
    THEOLOGY_VALIDATION_THRESHOLD: float = 0.85
    EMOTION_DIMENSIONS: int = 36


settings = Settings()
