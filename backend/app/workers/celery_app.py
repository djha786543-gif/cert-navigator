"""
Celery application — the "Heavy Worker" process.

This process is SEPARATE from the web server (FastAPI/uvicorn).
It handles all CPU-intensive and long-running work:
  - PDF resume parsing for bulk uploads         (Phase 1)
  - Study Guide / Practice Exam generation       (Phase 3)
  - Cheat Sheet PDF rendering                    (Phase 3)
  - Bulk job scraping (Adzuna + Reed + JSearch)  (Phase 2)
  - LLM artifact generation (GPT-4o / Claude)   (Phase 3)

⚠️ CAPACITY FLAGS:
  - LLM generation tasks (Phase 3): A single 3,000-token study guide takes
    ~15-30s and costs ~$0.15 (GPT-4o) or ~$0.12 (Claude Sonnet).
    50 concurrent requests = $7.50 burst cost + 30s latency for queued tasks.
    RECOMMENDATION: Rate-limit to 5 concurrent LLM tasks locally.
    AWS migration trigger: When daily generation > 200 artifacts → Lambda.

  - Bulk job scraping: Adzuna free tier = 250 req/day. For 50 users × 3 API
    calls each = 150 calls. SAFE locally. Exceeds limit at ~84 users → upgrade
    or use JSearch as primary with Adzuna as fallback.

  - Memory: Each Celery worker process loads the sentence-transformers model
    (~600 MB). Run --concurrency=2 on local machines with < 8 GB RAM.

Window 3 (Background Worker) command:
    celery -A backend.app.workers.celery_app worker --loglevel=info --concurrency=2
"""
from celery import Celery

from ..config import settings

celery_app = Celery(
    "career_navigator",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "backend.app.workers.tasks",
    ],
)

celery_app.conf.update(
    # Serialisation
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    # Timezone
    timezone="America/Los_Angeles",
    enable_utc=True,
    # Routing — heavy tasks go to "heavy" queue, light tasks to "default"
    task_routes={
        "backend.app.workers.tasks.generate_artifact": {"queue": "heavy"},
        "backend.app.workers.tasks.bulk_scrape_jobs": {"queue": "heavy"},
        "backend.app.workers.tasks.parse_resume_async": {"queue": "default"},
        "backend.app.workers.tasks.refresh_job_cache": {"queue": "default"},
    },
    # Timeouts
    task_soft_time_limit=120,    # 2 min soft limit — task gets SoftTimeLimitExceeded
    task_time_limit=180,         # 3 min hard limit — worker is killed and restarted
    # Result expiry (1 hour — client polls within this window)
    result_expires=3600,
    # Concurrency hint (override with --concurrency flag at runtime)
    worker_concurrency=2,
    # ⚠️ CAPACITY FLAG: Prefetch 1 task at a time so heavy tasks don't starve
    # light tasks. Increase to 4 if all tasks are quick (<5s).
    worker_prefetch_multiplier=1,
)
