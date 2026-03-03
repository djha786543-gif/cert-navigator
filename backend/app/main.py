"""
FastAPI application entry point — Resilience-Linked Career Engine v2.0

Architecture:
  Web Layer: FastAPI (uvicorn --workers 4) ─── handles auth, profile, job/cert/plan APIs
  Worker Layer: Celery + Redis ─────────────── handles PDF gen, LLM artifacts, bulk scraping

Startup sequence:
  1. Enable pgvector extension + create tables (init_db)
  2. Warm up sentence-transformers model (warm_up) — prevents cold-start on first upload
  3. Register routers
  4. Start APScheduler for daily job cache refresh

⚠️ CAPACITY SUMMARY for 50 concurrent users:
  - Web: uvicorn --workers 4 → 4 × 1,000 async req/s = ample headroom
  - DB: asyncpg pool_size=20 → 20 concurrent DB connections (sufficient)
  - Embedding: model loaded once per worker → 4 × 600 MB = 2.4 GB RAM needed
  - Celery: --concurrency=2 → 2 parallel heavy tasks (LLM gen + PDF parse)

Run command (Window 2 — Web API):
    uvicorn backend.app.main:app --host 0.0.0.0 --port 8001 --workers 4 --reload

Run command (Window 3 — Background Worker):
    celery -A backend.app.workers.celery_app worker --loglevel=info --concurrency=2
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from .config import settings
from .database import close_db, init_db
from .metrics import instrument_app                          # Phase 7
from .middleware.request_logging import RequestLoggingMiddleware  # Phase 7
from .routers import auth, users
from .routers.artifacts import router as artifacts_router
from .routers.ws_artifacts import router as ws_router
from .routers.resilience import router as resilience_router
from .routers.proctor import router as proctor_router
from .routers.skills_gap import router as skills_gap_router

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# ── Lifespan (startup + shutdown) ─────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ───────────────────────────────────────────────────────────
    logger.info("=== Career Navigator v2 starting up ===")

    # 1. Database
    logger.info("[1/3] Initialising PostgreSQL + pgvector...")
    try:
        await init_db()
    except Exception as e:
        logger.error(
            "DB init failed: %s\n"
            "⚠️  Is PostgreSQL running? Start with: docker-compose up postgres -d",
            e,
        )

    # 2. Embedding model warm-up
    logger.info("[2/3] Warming up embedding model (all-MiniLM-L6-v2, 384 dims)...")
    try:
        from .services.skill_vectorizer import warm_up
        await warm_up()
    except Exception as e:
        logger.warning("Embedding warm-up skipped: %s", e)

    # 3. APScheduler (daily job cache refresh at 06:00 PT)
    logger.info("[3/3] Starting APScheduler...")
    try:
        _start_scheduler()
    except Exception as e:
        logger.warning("Scheduler start failed: %s", e)

    logger.info("=== Startup complete. API ready at http://0.0.0.0:8001 ===")
    yield

    # ── Shutdown ──────────────────────────────────────────────────────────
    logger.info("Shutting down...")
    await close_db()
    logger.info("Bye.")


def _start_scheduler():
    """Daily 06:00 PT job-cache refresh via APScheduler."""
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from apscheduler.triggers.cron import CronTrigger

        scheduler = AsyncIOScheduler(timezone="America/Los_Angeles")
        scheduler.add_job(
            _daily_refresh,
            CronTrigger(hour=6, minute=0),
            id="daily_job_refresh",
            replace_existing=True,
        )
        scheduler.start()
        logger.info("APScheduler started — daily refresh at 06:00 PT")
    except ImportError:
        logger.warning("APScheduler not installed — skipping daily refresh")


async def _daily_refresh():
    """Triggered at 06:00 PT — refresh job cache for all active users."""
    logger.info("Daily job cache refresh triggered")
    # Phase 2 will implement bulk per-user refresh via Celery tasks


# ── Application ────────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Resilience-Linked Career Engine — async FastAPI backend "
        "with PostgreSQL + pgvector, Celery workers, and JWT auth."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── Middleware ─────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1024)
app.add_middleware(RequestLoggingMiddleware)  # Phase 7 — structured JSON access logs
instrument_app(app)                          # Phase 7 — Prometheus /metrics endpoint

# ── Routers ────────────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(artifacts_router)   # Phase 3: Study Vault
app.include_router(ws_router)           # Phase 3: WebSocket progress
app.include_router(resilience_router)  # Phase 4: Disruption Forecast + FAIR
app.include_router(proctor_router)     # Phase 5: Simulation Mode + Proctored Readiness
app.include_router(skills_gap_router)  # Skills gap analyzer service

# Phase 2, 5 routers added here as they're implemented:
# app.include_router(jobs.router)
# app.include_router(certs.router)
# app.include_router(career.router)


# ── Health check ───────────────────────────────────────────────────────────
@app.get("/health", tags=["Health"])
async def health():
    """
    Lightweight liveness probe.
    Load balancer / Docker HEALTHCHECK hits this every 10s.
    """
    return {
        "status": "ok",
        "version": settings.APP_VERSION,
        "market_default": settings.DEFAULT_MARKET,
    }


@app.get("/health/db", tags=["Health"])
async def health_db():
    """Check DB connectivity — used by readiness probe."""
    from sqlalchemy import text
    from .database import engine

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"db": "ok"}
    except Exception as e:
        return {"db": "error", "detail": str(e)}


# ── Dev entry point ────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.app.main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        workers=1,  # reload mode only supports 1 worker
    )
