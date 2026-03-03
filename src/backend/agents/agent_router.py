"""
FastAPI router exposing agent endpoints.
Mounts at /api/agents/ in the main app.

Endpoints:
  POST /api/agents/infer          — Run Resume Inference Agent (Phase 1)
  GET  /api/agents/task/{task_id} — Poll Celery task status
  GET  /api/agents/list           — List all registered agents
"""
import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, Optional

from .agent_registry import dispatch, list_agents

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/agents", tags=["Agents"])


class InferRequest(BaseModel):
    profile: Dict[str, Any]
    market: str = "US"


class AgentResponse(BaseModel):
    success: bool
    agent_name: str
    data: Dict[str, Any]
    duration_ms: int
    capacity_warnings: list = []
    error: Optional[str] = None


@router.post("/infer", response_model=AgentResponse)
async def run_inference(request: InferRequest):
    """
    Phase 1 — Resume Inference Agent endpoint.

    Enriches a parsed resume profile with:
    - Inferred hidden competencies
    - Skill trajectory (Declining / Augmented / Resilient)
    - Market Readiness Vector (10-dim, 0-100 per dimension)
    - Market Pressure Index (Gold Standard stat card metric)

    Runs inline (< 2s response). Falls back to Celery queue if it exceeds
    the MEDIUM tier timeout (10s).
    """
    result = await dispatch(
        "resume_inference",
        {"profile": request.profile, "market": request.market},
    )
    return AgentResponse(
        success=result.success,
        agent_name=result.agent_name,
        data=result.data,
        duration_ms=result.duration_ms,
        capacity_warnings=result.capacity_warnings,
        error=result.error,
    )


@router.get("/task/{task_id}")
async def poll_task(task_id: str):
    """
    Poll a Celery task for progress / result.
    Used by the WebSocket fallback (polling mode for clients without WS support).

    Returns:
      state: PENDING | PROGRESS | SUCCESS | FAILURE
      progress_pct: 0-100 (available during PROGRESS state)
      result: the agent output (available in SUCCESS state)
    """
    try:
        from celery.result import AsyncResult
        from ..workers.celery_app import celery_app

        task_result = AsyncResult(task_id, app=celery_app)
        state = task_result.state

        if state == "PENDING":
            return {"state": "PENDING", "progress_pct": 0}
        elif state == "PROGRESS":
            meta = task_result.info or {}
            return {
                "state": "PROGRESS",
                "progress_pct": meta.get("progress_pct", 0),
                "message": meta.get("message", ""),
            }
        elif state == "SUCCESS":
            return {"state": "SUCCESS", "progress_pct": 100, "result": task_result.result}
        elif state == "FAILURE":
            return {"state": "FAILURE", "error": str(task_result.result)}
        else:
            return {"state": state}
    except Exception as exc:
        raise HTTPException(500, f"Task polling failed: {exc}") from exc


@router.get("/list")
async def list_all_agents():
    """List all registered agents and their resource tiers."""
    return {
        "agents": list_agents(),
        "tiers": {
            "light": "Runs inline, < 500ms",
            "medium": "Runs inline with 10s timeout, falls back to Celery",
            "heavy": "Always queued via Celery (never blocks web server)",
        },
    }
