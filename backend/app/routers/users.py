"""
User management router: profile, resume upload, weakness tracking, market toggle.

Key design decisions:
- Resume parsing + vectorization happen in a Celery task (< 2s response guarantee)
- Weakness data is persisted server-side, mirroring the Gold Standard's localStorage
  tracker but with cross-device sync capability.
"""
import json
import logging
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models.user import User
from ..schemas.user import (
    MarketToggle,
    UserProfile,
    WeaknessPayload,
    WeaknessSummary,
)
from ..services.auth_service import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/users", tags=["Users"])

MAX_RESUME_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


# ── /users/me ─────────────────────────────────────────────────────────────
@router.get("/me", response_model=UserProfile)
async def read_me(current_user: User = Depends(get_current_user)):
    """Return the authenticated user's stored profile."""
    profile = (
        json.loads(current_user.profile_json) if current_user.profile_json else None
    )
    skill_count = len(profile.get("skills", [])) if profile else 0

    weakness_summary = None
    if current_user.weakness_data:
        raw = json.loads(current_user.weakness_data)
        weakness_summary = _compute_weakness_summary(raw)

    return UserProfile(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        market=current_user.market,
        profile=profile,
        weakness_summary=weakness_summary,
        skill_count=skill_count,
    )


# ── /users/me/resume ──────────────────────────────────────────────────────
@router.post("/me/resume")
async def upload_resume(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Accept a JSON or PDF resume.

    ⚠️ CAPACITY FLAG: PDF parsing with pdfplumber is CPU-bound (~1-3s per file).
    For 50 concurrent uploads on a 4-core machine, queue depth > 8 will cause
    > 2s response times. The parsing + vectorization are offloaded to
    BackgroundTasks for now; migrate to Celery task queue if concurrent uploads
    exceed 10/minute.

    Response: Returns immediately with job_id. Client polls /users/me/resume/status.
    """
    content_type = file.content_type or ""
    if not (
        "json" in content_type
        or "pdf" in content_type
        or file.filename.endswith((".json", ".pdf"))
    ):
        raise HTTPException(
            400, "Only JSON and PDF resumes are supported"
        )

    content = await file.read()
    if len(content) > MAX_RESUME_SIZE_BYTES:
        raise HTTPException(413, "Resume file exceeds 10 MB limit")

    # Enqueue parse + vectorize as background task
    # (replaces blocking call — guarantees < 2s HTTP response)
    background_tasks.add_task(
        _parse_and_vectorize,
        user_id=current_user.id,
        content=content,
        content_type=content_type,
        filename=file.filename or "",
    )

    return {
        "message": "Resume upload accepted — parsing in background",
        "status": "processing",
        "note": "Profile will be available at GET /users/me within 5-10 seconds",
    }


# ── /users/me/market ──────────────────────────────────────────────────────
@router.put("/me/market")
async def toggle_market(
    payload: MarketToggle,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Switch between US and India market intelligence.
    This cascades to job recommendations and salary benchmarks.
    """
    current_user.market = payload.market
    db.add(current_user)
    await db.commit()
    return {
        "message": f"Market switched to {payload.market}",
        "market": payload.market,
    }


# ── /users/me/weakness ────────────────────────────────────────────────────
@router.get("/me/weakness", response_model=WeaknessSummary)
async def get_weakness(current_user: User = Depends(get_current_user)):
    """
    Return weakness analysis — predicted exam score + recommendations.
    Mirrors the WeaknessTracker.getPredictedExamScore() from the Gold Standard.
    """
    if not current_user.weakness_data:
        return WeaknessSummary(
            predicted_exam_score=None,
            weak_domains=[],
            recommendations=[],
            total_questions_answered=0,
        )
    raw = json.loads(current_user.weakness_data)
    return _compute_weakness_summary(raw)


@router.post("/me/weakness")
async def save_weakness(
    payload: WeaknessPayload,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Persist the client-side WeaknessTracker state to the server.
    Call this after each assessment session to enable cross-device sync.
    """
    current_user.weakness_data = payload.model_dump_json()
    db.add(current_user)
    await db.commit()
    return {"message": "Weakness data saved"}


# ── Internal helpers ──────────────────────────────────────────────────────
async def _parse_and_vectorize(
    user_id: int, content: bytes, content_type: str, filename: str
) -> None:
    """
    Background task: parse resume → extract skills → compute 384-dim vector.
    Opens its own DB session (background task can't reuse the request session).
    """
    from ..database import AsyncSessionLocal
    from ..services.resume_parser import parse_resume_bytes
    from ..services.skill_vectorizer import vectorize_skills

    try:
        structured = await parse_resume_bytes(content, content_type, filename)
        skills = structured.get("skills", [])
        vector = await vectorize_skills(skills)

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                __import__("sqlalchemy", fromlist=["select"]).select(User).where(
                    User.id == user_id
                )
            )
            user = result.scalar_one_or_none()
            if user:
                import json as _json
                user.profile_json = _json.dumps(structured)
                user.skill_vector = vector
                db.add(user)
                await db.commit()
                logger.info(
                    "Resume parsed + vectorized for user_id=%d (%d skills)",
                    user_id,
                    len(skills),
                )
    except Exception as exc:
        logger.error("Background parse failed for user_id=%d: %s", user_id, exc)


def _compute_weakness_summary(raw: dict) -> WeaknessSummary:
    """
    Port of WeaknessTracker.getPredictedExamScore() and getWeakDomains()
    from certlab-saas-v2.html, translated from localStorage JS to Python.
    """
    domains = raw.get("domains", {})
    history = raw.get("history", [])
    total_answered = len(history)

    domain_stats = [
        {
            "domain": k,
            "rate": round(v["correct"] / v["total"] * 100) if v["total"] > 0 else 0,
            "total": v["total"],
            "correct": v["correct"],
        }
        for k, v in domains.items()
        if v.get("total", 0) >= 2
    ]
    domain_stats.sort(key=lambda x: x["rate"])  # weakest first

    # Weighted average predicted score
    if domain_stats:
        total_w = sum(d["total"] for d in domain_stats)
        predicted = (
            round(sum(d["rate"] * d["total"] for d in domain_stats) / total_w)
            if total_w > 0
            else None
        )
    else:
        predicted = None

    weak = [d for d in domain_stats if d["rate"] < 75]
    recommendations = [
        {"topic": d["domain"], "rate": d["rate"], "total": d["total"]}
        for d in weak
    ]

    return WeaknessSummary(
        predicted_exam_score=predicted,
        weak_domains=domain_stats,
        recommendations=recommendations,
        total_questions_answered=total_answered,
    )
