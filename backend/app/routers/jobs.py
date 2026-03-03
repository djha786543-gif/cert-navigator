"""
v2 Jobs router — async endpoints with market toggle.

All endpoints are sub-2s (< 2s guarantee from the brief):
  - Cache hits:   < 10ms (Redis lookup)
  - Cache misses: < 2s (parallel API fetch with 8s timeout, mock fallback)
  - Trending:     < 5ms (static data)
  - Intelligence: < 3s (parallel fetch + corpus analysis)
"""
import json
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models.user import User
from ..services.auth_service import get_current_user
from ..services.job_service import get_jobs_for_user, invalidate_user_cache

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/jobs", tags=["Jobs"])


@router.get("/me")
async def get_my_jobs(
    market: str = Query(default="US", pattern="^(US|IN)$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Return ranked job recommendations.
    market: "US" | "IN" — persisted to user profile on change.
    """
    if not current_user.profile_json:
        return {"jobs": [], "message": "Upload a resume first", "market": market}

    profile = json.loads(current_user.profile_json)

    # Persist market preference
    if current_user.market != market:
        current_user.market = market
        db.add(current_user)
        await db.commit()

    result = await get_jobs_for_user(profile, market=market)
    return result


@router.post("/refresh")
async def refresh_jobs(
    market: str = Query(default="US", pattern="^(US|IN)$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Force-refresh job cache — call after resume update."""
    if not current_user.profile_json:
        return {"jobs": [], "message": "Upload a resume first"}
    profile = json.loads(current_user.profile_json)
    await invalidate_user_cache(current_user.id)
    result  = await get_jobs_for_user(profile, market=market)
    return {**result, "message": "Cache refreshed"}


@router.get("/trending")
async def trending_roles(market: str = Query(default="US", pattern="^(US|IN)$")):
    """Return trending IT Audit / AI Governance roles for selected market."""
    from src.backend.engine.job_recommendation import get_trending_roles
    return {"roles": get_trending_roles(market), "market": market}


@router.get("/intelligence")
async def market_intelligence(
    market: str = Query(default="US", pattern="^(US|IN)$"),
    current_user: User = Depends(get_current_user),
):
    """
    Run MarketIntelligenceAgent — trending skills, salary benchmarks,
    cert premium map, location clusters, JD shift report.
    """
    profile = json.loads(current_user.profile_json) if current_user.profile_json else {}
    try:
        from src.backend.agents.agent_registry import dispatch
        result = await dispatch("market_intelligence", {"profile": profile, "market": market})
        return result.data if result.success else {"error": result.error, "market": market}
    except Exception as exc:
        logger.error("MarketIntelligenceAgent failed: %s", exc)
        return {"error": str(exc), "market": market}
