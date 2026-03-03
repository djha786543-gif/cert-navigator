"""
Celery tasks — the actual units of background work.

Phase 1: parse_resume_async, refresh_job_cache
Phase 3: generate_artifact (study guides, practice exams, cheat sheets)
Phase 2: bulk_scrape_jobs

Each task reports progress via the Celery result backend so the frontend
can poll task_id → {state, progress_pct, eta_seconds} for real-time UX.

⚠️ CAPACITY FLAG for generate_artifact:
  A single study guide generation (3,000 tokens) takes 15-30s on the LLM API.
  At 50 concurrent requests, tasks queue behind 5 concurrent LLM slots.
  Latency for task #50 = ceil(50/5) × 30s = 300s (5 minutes).
  MITIGATION: Pre-cache common artifacts (AIGP, CISA study guides) at startup.
  AWS MIGRATION TRIGGER: Daily artifact requests > 200 → offload to Lambda.
"""
import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

from celery import Task
from celery.utils.log import get_task_logger

from .celery_app import celery_app

logger = get_task_logger(__name__)


# ── Base task class with progress reporting ────────────────────────────────
class ProgressTask(Task):
    """Base class that adds update_progress() helper."""

    def update_progress(self, pct: int, message: str = "") -> None:
        self.update_state(
            state="PROGRESS",
            meta={"progress_pct": pct, "message": message},
        )


# ── Phase 1: Resume parsing ────────────────────────────────────────────────
@celery_app.task(bind=True, base=ProgressTask, name="backend.app.workers.tasks.parse_resume_async")
def parse_resume_async(
    self: ProgressTask,
    user_id: int,
    content_b64: str,
    content_type: str,
    filename: str,
) -> Dict[str, Any]:
    """
    Full async-safe resume parse + vectorize, executed in Celery worker.
    Use this when BackgroundTasks queue depth > 10 concurrent uploads.

    Payload: content is base64-encoded bytes (JSON-serialisable for Celery).
    """
    import base64

    self.update_progress(10, "Decoding resume...")
    content = base64.b64decode(content_b64)

    self.update_progress(30, "Parsing resume content...")
    structured = asyncio.run(_run_parse(content, content_type, filename))

    self.update_progress(60, "Vectorizing skills...")
    skills = structured.get("skills", [])
    vector = asyncio.run(_run_vectorize(skills))

    self.update_progress(80, "Saving to database...")
    _save_to_db(user_id, structured, vector)

    self.update_progress(100, "Complete")
    return {
        "status": "success",
        "user_id": user_id,
        "skill_count": len(skills),
        "profile": structured,
    }


# ── Phase 2: Job cache refresh ─────────────────────────────────────────────
@celery_app.task(bind=True, base=ProgressTask, name="backend.app.workers.tasks.refresh_job_cache")
def refresh_job_cache(
    self: ProgressTask,
    user_id: int,
    market: str = "US",
) -> Dict[str, Any]:
    """
    Refresh cached job recommendations for a single user.
    Scheduled by APScheduler daily at 06:00 PT.
    """
    self.update_progress(20, f"Fetching {market} job listings...")
    # Phase 2 implementation — placeholder returns success
    self.update_progress(100, "Job cache refreshed")
    return {"status": "success", "user_id": user_id, "market": market, "job_count": 0}


# ── Phase 3: AI Artifact Generator ────────────────────────────────────────
@celery_app.task(
    bind=True,
    base=ProgressTask,
    name="backend.app.workers.tasks.generate_artifact",
    max_retries=2,
    default_retry_delay=30,
)
def generate_artifact(
    self: ProgressTask,
    user_id: int,
    artifact_type: str,   # "study_guide" | "practice_exam" | "cheat_sheet"
    cert_id: str,         # "aigp" | "cisa" | "aaia" | "ciasp"
    domain_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generate an AI-powered artifact matching the certlab-saas-v2.html Gold Standard depth.

    ⚠️ CAPACITY FLAG: Each call makes 1-3 LLM API requests (15-30s each).
    Rate-limited to 5 concurrent tasks via Celery routing queue 'heavy'.
    Monitor with: celery -A backend.app.workers.celery_app inspect active

    WebSocket progress: The frontend subscribes to ws://.../ws/artifact/{task_id}
    which emits { progress_pct, stage, eta_seconds } every 2 seconds.
    (Phase 3 implementation)
    """
    logger.info(
        "generate_artifact: user=%d type=%s cert=%s domain=%s",
        user_id, artifact_type, cert_id, domain_id,
    )

    self.update_progress(5, f"Initialising {artifact_type} generator for {cert_id.upper()}...")

    try:
        # Phase 3: ArtifactSovereignAgent — 3-node pipeline
        # (Research → Synthesis → Adversarial)
        result = asyncio.run(_run_artifact_sovereign(
            user_id, artifact_type, cert_id, domain_id, task=self
        ))
        self.update_progress(100, "Artifact generation complete")
        return {
            "status":       "success",
            "artifact_type": artifact_type,
            "cert_id":       cert_id,
            "artifact":      result.get("artifact"),
            "cert":          result.get("cert"),
            "node_trace":    result.get("node_trace", []),
        }

    except Exception as exc:
        logger.error("Artifact generation failed: %s", exc)
        raise self.retry(exc=exc)


# ── Phase 2: Bulk scraping ─────────────────────────────────────────────────
@celery_app.task(
    bind=True,
    base=ProgressTask,
    name="backend.app.workers.tasks.bulk_scrape_jobs",
)
def bulk_scrape_jobs(
    self: ProgressTask,
    market: str = "US",
    keywords: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Scrape jobs from Adzuna + Reed + JSearch simultaneously.
    Results are cached in Redis (TTL: 6 hours).

    ⚠️ CAPACITY FLAG: Adzuna free tier = 250 req/day.
    Reed.co.uk free tier = 150 req/day (India/UK market).
    JSearch (RapidAPI) = 500 req/month on free tier.
    For > 50 users on US market: upgrade Adzuna or add Indeed Publisher API.
    """
    self.update_progress(10, f"Starting {market} market scrape...")
    # Phase 2 implementation
    self.update_progress(100, "Scrape complete")
    return {"status": "success", "market": market, "jobs_found": 0}


# ── Internal helpers ───────────────────────────────────────────────────────
async def _run_artifact_sovereign(
    user_id: int,
    artifact_type: str,
    cert_id: str,
    domain_id: Optional[str],
    task=None,
) -> Dict[str, Any]:
    """Run ArtifactSovereignAgent inline from Celery worker context."""
    from src.backend.agents.artifact_sovereign_agent import ArtifactSovereignAgent
    agent = ArtifactSovereignAgent()
    result = await agent.run({
        "cert_id":       cert_id,
        "artifact_type": artifact_type,
        "domain_id":     domain_id,
        "profile":       {"user_id": user_id},
        "task":          task,
    })
    if result.success:
        return result.data
    raise RuntimeError(result.error or "ArtifactSovereignAgent failed")


async def _run_parse(content: bytes, content_type: str, filename: str) -> Dict[str, Any]:
    from ..services.resume_parser import parse_resume_bytes
    return await parse_resume_bytes(content, content_type, filename)


async def _run_vectorize(skills: List[str]) -> List[float]:
    from ..services.skill_vectorizer import vectorize_skills
    return await vectorize_skills(skills)


def _save_to_db(user_id: int, structured: Dict, vector: List[float]) -> None:
    """Synchronous DB write from Celery worker (uses sync SQLAlchemy)."""
    import sqlalchemy as sa
    from ..config import settings

    # Build a synchronous engine for the Celery worker context
    sync_url = settings.DATABASE_URL.replace("+asyncpg", "")
    engine = sa.create_engine(sync_url)
    with engine.connect() as conn:
        conn.execute(
            sa.text(
                "UPDATE users SET profile_json = :profile, skill_vector = :vec "
                "WHERE id = :uid"
            ),
            {
                "profile": json.dumps(structured),
                "vec": str(vector),
                "uid": user_id,
            },
        )
        conn.commit()


