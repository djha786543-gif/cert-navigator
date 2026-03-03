"""
Phase 2 – Background Scheduler

Runs a daily job-refresh sweep at 06:00 America/Los_Angeles using APScheduler.
The in-memory cache (_daily_cache) is sufficient for a single-server deployment;
swap for a Redis or DB-backed store when scaling horizontally.

Usage (in main.py):
    from src.backend.scheduler import start_scheduler, stop_scheduler
    app.on_event("startup")(start_scheduler)
    app.on_event("shutdown")(stop_scheduler)
"""
import logging
from datetime import datetime
from typing import Any, Dict, List

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

# ── In-memory job cache: { user_id: [job_dict, ...] } ────────────────────────
_daily_cache: Dict[int, List[Dict[str, Any]]] = {}
_last_refresh: datetime | None = None

scheduler = BackgroundScheduler(timezone="America/Los_Angeles")


# ── Public interface ───────────────────────────────────────────────────────────

def start_scheduler() -> None:
    """Register cron jobs and start the background scheduler."""
    scheduler.add_job(
        _daily_sweep,
        CronTrigger(hour=6, minute=0),
        id="daily_job_refresh",
        replace_existing=True,
        misfire_grace_time=3600,   # allow up to 1 h late start
    )
    if not scheduler.running:
        scheduler.start()
    logger.info("[Scheduler] Started — daily job refresh fires at 06:00 PT")


def stop_scheduler() -> None:
    """Gracefully stop the scheduler on application shutdown."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("[Scheduler] Stopped")


def get_cached_jobs(user_id: int) -> List[Dict[str, Any]]:
    """Return the most recent job list for a user (may be empty before first refresh)."""
    return _daily_cache.get(user_id, [])


def refresh_jobs_for_user(user_id: int, profile: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Force-refresh the job cache for a single user.
    Called on login and after a resume upload so the user always sees fresh results.
    """
    from src.backend.engine.job_recommendation import recommend_jobs

    jobs = recommend_jobs(profile)
    _daily_cache[user_id] = jobs
    logger.info("[Scheduler] Refreshed %d jobs for user %d", len(jobs), user_id)
    return jobs


def get_last_refresh_time() -> str | None:
    """Return the ISO timestamp of the last scheduled sweep, or None."""
    return _last_refresh.isoformat() if _last_refresh else None


# ── Internal sweep ─────────────────────────────────────────────────────────────

def _daily_sweep() -> None:
    """
    Iterates all users who have a cached profile and refreshes their job list.
    In production, fetch active users directly from the database.
    """
    global _last_refresh
    _last_refresh = datetime.utcnow()

    # Lazy import to avoid circular dependency at module load time
    from src.backend.engine.job_recommendation import recommend_jobs
    from src.backend.user_management import SessionLocal, UserModel
    import json

    db = SessionLocal()
    try:
        users = db.query(UserModel).filter(UserModel.profile_json.isnot(None)).all()
        refreshed = 0
        for user in users:
            try:
                profile = json.loads(user.profile_json)
                _daily_cache[user.id] = recommend_jobs(profile)
                refreshed += 1
            except Exception as exc:
                logger.error("[Scheduler] Failed to refresh user %d: %s", user.id, exc)
        logger.info(
            "[Scheduler] Daily sweep complete at %s — %d/%d users refreshed",
            _last_refresh.isoformat(), refreshed, len(users),
        )
    finally:
        db.close()
