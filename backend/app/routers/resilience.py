"""
v2 Resilience router — Phase 4 disruption forecasting and FAIR calculator.

Endpoints:
  GET  /api/resilience/forecast          — full 5-year resilience forecast
  GET  /api/resilience/disruption-audit  — lightweight per-skill audit
  POST /api/resilience/fair-calc         — FAIR Model calculator (no auth)

⚠️ CAPACITY FLAG: ResilienceForecasterAgent is MEDIUM tier.
  Pure Python computation, <50ms per call.
  Safe for 50 concurrent users inline — no Celery needed.
"""
import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models.user import User
from ..services.auth_service import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/resilience", tags=["Resilience"])


class FairCalcRequest(BaseModel):
    tef:            float
    vulnerability:  float
    primary_loss:   int
    secondary_loss: int = 0


@router.get("/forecast")
async def resilience_forecast(
    market: str = "US",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Full 5-year resilience forecast with FAIR model and mitigation roadmap."""
    profile = json.loads(current_user.profile_json) if current_user.profile_json else {}
    if not profile:
        raise HTTPException(status_code=400, detail="Upload a resume first.")
    from src.backend.agents.resilience_forecaster_agent import ResilienceForecasterAgent
    agent  = ResilienceForecasterAgent()
    result = await agent.run({"profile": profile, "market": market.upper()})
    if result.success:
        return result.data
    raise HTTPException(status_code=500, detail=result.error)


@router.get("/disruption-audit")
async def disruption_audit(
    market: str = "US",
    current_user: User = Depends(get_current_user),
):
    profile = json.loads(current_user.profile_json) if current_user.profile_json else {}
    if not profile:
        raise HTTPException(status_code=400, detail="Upload a resume first.")
    from src.backend.agents.resilience_forecaster_agent import ResilienceForecasterAgent
    agent  = ResilienceForecasterAgent()
    result = await agent.run({"profile": profile, "market": market.upper()})
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)
    d = result.data
    return {
        "resilience_score":     d["resilience_score"],
        "disruption_signal":    d["disruption_signal"],
        "skill_audit":          d["skill_audit"],
        "resilience_breakdown": d["resilience_breakdown"],
        "fair_ale":             d["fair_model"]["ale"],
        "fair_ale_label":       d["fair_model"]["ale_label"],
    }


@router.post("/fair-calc")
def fair_calculator(req: FairCalcRequest):
    """Standalone FAIR Model calculator — no auth required."""
    from src.backend.agents.resilience_forecaster_agent import compute_fair_from_inputs
    if not (0 <= req.vulnerability <= 1):
        raise HTTPException(status_code=422, detail="vulnerability must be 0–1")
    if req.tef < 0:
        raise HTTPException(status_code=422, detail="tef must be non-negative")
    return compute_fair_from_inputs(
        tef=req.tef,
        vulnerability=req.vulnerability,
        primary_loss=req.primary_loss,
        secondary_loss=req.secondary_loss,
    )
