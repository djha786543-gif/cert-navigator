"""
Centralised settings via pydantic-settings.
All runtime values are pulled from environment variables or .env file.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")

    # ── Application ──────────────────────────────────────────────────────────
    APP_NAME: str = "Career Navigator — Resilience Engine"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = False

    # ── Security / JWT ────────────────────────────────────────────────────────
    SECRET_KEY: str = "change-me-in-production-use-openssl-rand-hex-32"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8-hour sessions

    # ── Database (PostgreSQL + pgvector) ──────────────────────────────────────
    # ⚠️ CAPACITY FLAG: asyncpg pool_size=20 supports ~50 concurrent users
    # with typical short-lived queries. If p95 DB latency > 200ms, increase
    # pool_size or migrate to Supabase connection pooler (PgBouncer).
    DATABASE_URL: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/career_navigator"
    )
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_PRE_PING: bool = True

    # ── Redis / Celery ────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"

    # ── Embedding Model ───────────────────────────────────────────────────────
    # ⚠️ CAPACITY FLAG: all-MiniLM-L6-v2 loads ~600 MB into RAM once at startup.
    # With uvicorn --workers 4, multiply by 4 → ~2.4 GB RAM required.
    # On machines with < 8 GB RAM, use --workers 1 and rely on async concurrency.
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    EMBEDDING_DIM: int = 384

    # ── External Job APIs ─────────────────────────────────────────────────────
    ADZUNA_APP_ID: str = ""
    ADZUNA_APP_KEY: str = ""
    REED_API_KEY: str = ""          # UK / India market
    JSEARCH_API_KEY: str = ""       # Rapid API — JSearch (backup)

    # ── Market Toggle ─────────────────────────────────────────────────────────
    DEFAULT_MARKET: str = "US"      # "US" | "IN"

    # ── CORS ──────────────────────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://192.168.1.54:3000",
    ]

    # ── LLM (Phase 3) ─────────────────────────────────────────────────────────
    # ⚠️ CAPACITY FLAG: Generating a 3,000-token study guide takes ~15-30s on
    # GPT-4o and costs ~$0.15/artifact. For 50 concurrent requests that means
    # a burst cost of $7.50 and potential 30s+ waits. Must use Celery queue.
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    LLM_PROVIDER: str = "anthropic"  # "openai" | "anthropic"
    LLM_MAX_TOKENS: int = 4096


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
