"""
v2 Artifacts router — async endpoints for the Study Vault.

Endpoints:
  GET  /api/artifacts/catalog                 — list certs + artifact types
  POST /api/artifacts/generate                — queue artifact generation (Celery HEAVY)
  GET  /api/artifacts/task/{task_id}          — poll Celery task status + progress
  GET  /api/artifacts/cert/{cert_id}          — cert metadata with domain breakdown
  POST /api/artifacts/generate/inline        — direct generation (no Celery, for dev)

WebSocket progress:
  WS   /ws/artifact/{task_id}                 — real-time progress (see ws_artifacts.py)

⚠️ CAPACITY FLAG: generate_artifact is HEAVY tier — max 2 concurrent via Celery.
   For 50 users requesting artifacts simultaneously: queue depth = 48, wait ≈ 5 min.
   Mitigation: pre-cache AIGP and CISA study guides at startup (Phase 3 bonus).
   Migration trigger: >200 artifact requests/day → AWS Lambda + S3 pre-cache.
"""
import json
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models.user import User
from ..services.auth_service import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/artifacts", tags=["Artifacts"])


class ArtifactRequest(BaseModel):
    cert_id:       str            # "aigp" | "cisa" | "aaia" | "ciasp"
    artifact_type: str            # "study_guide" | "cheat_sheet" | "practice_exam"
    domain_id:     Optional[str] = None   # optional domain filter

    @field_validator("cert_id", "artifact_type")
    @classmethod
    def _must_be_nonempty(cls, v: str) -> str:
        if not isinstance(v, str) or not v.strip():
            raise ValueError("must be a non-empty string")
        return v.strip().lower()


# ── Catalog ────────────────────────────────────────────────────────────────

@router.get("/catalog")
async def artifacts_catalog():
    """Return available certifications and artifact types for the Study Vault."""
    from src.backend.agents.artifact_sovereign_agent import get_cert_catalog, get_artifact_types
    return {
        "certifications": list(get_cert_catalog().values()),
        "artifact_types": get_artifact_types(),
    }


@router.get("/cert/{cert_id}")
async def get_cert_info(cert_id: str):
    """Return certification metadata including domains and exam structure."""
    from src.backend.agents.artifact_sovereign_agent import get_cert_catalog
    catalog = get_cert_catalog()
    cert = catalog.get(cert_id.lower())
    if not cert:
        raise HTTPException(
            status_code=404,
            detail=f"Cert '{cert_id}' not found. Valid: {list(catalog.keys())}",
        )
    return cert


# ── Generation endpoints ───────────────────────────────────────────────────

@router.post("/generate")
async def generate_artifact(
    req: ArtifactRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Queue artifact generation via Celery HEAVY queue.
    Returns task_id for WebSocket polling.

    ⚠️ CAPACITY FLAG: Celery --concurrency=2 → max 2 parallel artifact tasks.
    Task #3 will wait in queue. For instant access, use /generate/inline.
    """
    profile = json.loads(current_user.profile_json) if current_user.profile_json else {}
    try:
        from backend.app.workers.tasks import generate_artifact as celery_task
        task = celery_task.delay(
            user_id=current_user.id,
            artifact_type=req.artifact_type,
            cert_id=req.cert_id,
            domain_id=req.domain_id,
        )
        return {
            "status":   "queued",
            "task_id":  task.id,
            "poll_url": f"/api/artifacts/task/{task.id}",
            "ws_url":   f"/ws/artifact/{task.id}",
            "message":  f"{req.cert_id.upper()} {req.artifact_type.replace('_',' ')} queued. Connect to ws_url for live progress.",
        }
    except Exception as exc:
        # Celery unavailable — run inline
        logger.warning("Celery unavailable, running artifact inline: %s", exc)
        return await _generate_inline(req, profile)


@router.post("/generate/inline")
async def generate_artifact_inline(
    req: ArtifactRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Generate artifact inline (no Celery required).
    Blocks for up to 30s. Use for development or when Celery is not running.
    """
    profile = json.loads(current_user.profile_json) if current_user.profile_json else {}
    return await _generate_inline(req, profile)


async def _generate_inline(req: ArtifactRequest, profile: Dict[str, Any]) -> Dict[str, Any]:
    """Shared inline generation logic."""
    from src.backend.agents.agent_registry import dispatch
    result = await dispatch(
        "artifact_sovereign",
        {
            "cert_id":       req.cert_id,
            "artifact_type": req.artifact_type,
            "domain_id":     req.domain_id,
            "profile":       profile,
        },
    )
    if result.success:
        return {
            "status":     "complete",
            "artifact":   result.data.get("artifact"),
            "cert":       result.data.get("cert"),
            "node_trace": result.data.get("node_trace", []),
            "duration_ms": result.duration_ms,
        }
    raise HTTPException(status_code=500, detail=result.error or "Artifact generation failed")


# ── Task polling ───────────────────────────────────────────────────────────

@router.get("/task/{task_id}")
async def get_task_status(task_id: str):
    """
    Poll Celery task status for artifact generation.
    Returns: { state, progress_pct, message, result (when done) }
    """
    try:
        from celery.result import AsyncResult
        from backend.app.workers.celery_app import celery_app

        ar = AsyncResult(task_id, app=celery_app)
        state = ar.state

        if state == "PENDING":
            return {"state": "PENDING", "progress_pct": 0, "message": "Queued…"}

        if state == "PROGRESS":
            meta = ar.info or {}
            return {
                "state":        "PROGRESS",
                "progress_pct": meta.get("progress_pct", 0),
                "message":      meta.get("message", "Processing…"),
            }

        if state == "SUCCESS":
            return {
                "state":        "SUCCESS",
                "progress_pct": 100,
                "message":      "Complete",
                "result":       ar.result,
            }

        if state == "FAILURE":
            return {
                "state":   "FAILURE",
                "message": str(ar.info),
                "progress_pct": 0,
            }

        return {"state": state, "progress_pct": 0}

    except Exception as exc:
        logger.error("Task status check failed: %s", exc)
        return {"state": "UNKNOWN", "error": str(exc)}
