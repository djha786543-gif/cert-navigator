"""
v2 Proctor router — Phase 5 Simulation Mode & Proctored Readiness.

Endpoints:
  POST /api/proctor/session/start             — create a new exam session
  GET  /api/proctor/session/{id}/question     — get current question
  POST /api/proctor/session/{id}/answer       — submit answer + adaptive feedback
  GET  /api/proctor/session/{id}/results      — full results + weakness heatmap
  GET  /api/proctor/weakness                  — aggregated weakness report
  GET  /api/proctor/catalog                   — available certs + question counts

⚠️ CAPACITY FLAG: ProctorAgent is HEAVY tier.
  Session creation: <5ms, pure Python. Safe inline for 50 concurrent users.
  Sessions are in-memory (module-level dict). Survives as long as the process.
  For multi-worker uvicorn (--workers 4): sessions are NOT shared between workers.
  v2 fix: back _SESSIONS with Redis using shared key namespace.
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models.user import User
from ..services.auth_service import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/proctor", tags=["Proctor"])


class SessionStartRequest(BaseModel):
    cert_id: str
    mode:    str  # "practice" | "exam"


class AnswerRequest(BaseModel):
    answer_index: int  # 0–3


@router.post("/session/start")
async def proctor_session_start(
    req:          SessionStartRequest,
    current_user: User = Depends(get_current_user),
    db:           AsyncSession = Depends(get_db),
):
    """Start a new proctored exam session."""
    from src.backend.agents.proctor_agent import create_session
    user_id = str(current_user.id)
    return create_session(
        cert_id=req.cert_id.lower(),
        mode=req.mode.lower(),
        user_id=user_id,
    )


@router.get("/session/{session_id}/question")
async def proctor_get_question(
    session_id:   str,
    current_user: User = Depends(get_current_user),
):
    """Return the current question without answer or explanation."""
    from src.backend.agents.proctor_agent import get_current_question
    result = get_current_question(session_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/session/{session_id}/answer")
async def proctor_submit_answer(
    session_id:   str,
    req:          AnswerRequest,
    current_user: User = Depends(get_current_user),
):
    """Submit an answer; returns feedback (immediate in practice, deferred in exam)."""
    from src.backend.agents.proctor_agent import submit_answer
    if not (0 <= req.answer_index <= 3):
        raise HTTPException(status_code=422, detail="answer_index must be 0–3")
    result = submit_answer(session_id, req.answer_index)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/session/{session_id}/results")
async def proctor_get_results(
    session_id:   str,
    current_user: User = Depends(get_current_user),
):
    """Return full results, readiness score, domain heatmap, answer review."""
    from src.backend.agents.proctor_agent import get_results
    result = get_results(session_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/weakness")
async def proctor_weakness(
    current_user: User = Depends(get_current_user),
):
    """Return aggregated weakness report across all past sessions."""
    from src.backend.agents.proctor_agent import get_weakness_report
    user_id = str(current_user.id)
    return get_weakness_report(user_id)


@router.get("/catalog")
async def proctor_catalog():
    """Return available certifications and question counts. No auth required."""
    from src.backend.agents.proctor_agent import _PROCTOR_QUESTION_BANK
    from src.backend.agents.artifact_sovereign_agent import (
        _QUESTION_BANK as _P3_BANK, CERT_CATALOG
    )
    catalog = []
    for cert_id, cert in CERT_CATALOG.items():
        p3_count = len(_P3_BANK.get(cert_id, []))
        p5_count = len(_PROCTOR_QUESTION_BANK.get(cert_id, []))
        catalog.append({
            "id":              cert_id,
            "name":            cert.get("name", cert_id.upper()),
            "acronym":         cert.get("acronym", cert_id.upper()),
            "total_questions": p3_count + p5_count,
            "practice_q":      10,
            "exam_q":          30,
        })
    return {"certifications": catalog}
