"""
v2 Job Service — async multi-API job fetcher for PostgreSQL backend.

Key upgrade over v1:
  - Uses asyncio.gather for true parallel API calls
  - Redis caching with 6-hour TTL (market-aware cache key)
  - pgvector skill-matching: job descriptions vectorized for cosine sim
  - Market toggle: US (Adzuna+JSearch) | IN (Reed+Adzuna-IN)

⚠️ CAPACITY FLAGS:
  Redis TTL caching: each user's job cache = ~20KB JSON.
  For 50 users × 20KB = 1MB of Redis storage (negligible).
  Cache invalidation: on resume update or manual refresh.
  API rate limits: see job_recommendation.py for per-source limits.
"""
import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

ADZUNA_APP_ID   = os.getenv("ADZUNA_APP_ID", "")
ADZUNA_APP_KEY  = os.getenv("ADZUNA_APP_KEY", "")
REED_API_KEY    = os.getenv("REED_API_KEY", "")
JSEARCH_API_KEY = os.getenv("JSEARCH_API_KEY", "")

_CACHE_TTL = 6 * 3600  # 6 hours in seconds


async def get_jobs_for_user(
    profile: Dict[str, Any],
    market: str = "US",
    max_results: int = 15,
    redis_client=None,
) -> Dict[str, Any]:
    """
    Main entry point: get ranked job recommendations with Redis caching.
    Falls back to live fetch if cache miss.
    """
    user_id = profile.get("id") or profile.get("email", "anon")
    cache_key = f"jobs:{user_id}:{market}"

    # Cache check
    if redis_client:
        try:
            cached = await redis_client.get(cache_key)
            if cached:
                data = json.loads(cached)
                data["source"] = "cache"
                return data
        except Exception as exc:
            logger.debug("Redis cache miss: %s", exc)

    # Live fetch
    result = await _fetch_all_sources(profile, market, max_results)

    # Cache result
    if redis_client and result.get("jobs"):
        try:
            await redis_client.setex(cache_key, _CACHE_TTL, json.dumps(result))
        except Exception as exc:
            logger.debug("Redis cache write failed: %s", exc)

    return result


async def _fetch_all_sources(
    profile: Dict[str, Any],
    market: str,
    max_results: int,
) -> Dict[str, Any]:
    """Parallel fetch from all enabled API sources."""
    role = profile.get("target_role") or profile.get("current_role") or "IT Audit"

    # Import the v1 engine for shared fetchers (DRY)
    from src.backend.engine.job_recommendation import (
        _fetch_adzuna_async,
        _fetch_reed_async,
        _fetch_jsearch_async,
        _mock_jobs_for_market,
        _rank_and_score,
        _analyze_market_intelligence,
    )

    async with httpx.AsyncClient(timeout=httpx.Timeout(8.0, connect=3.0)) as client:
        sources = await asyncio.gather(
            _fetch_adzuna_async(client, role, market),
            _fetch_reed_async(client, role, market),
            _fetch_jsearch_async(client, role, market),
            _mock_jobs_for_market(market),
            return_exceptions=True,
        )

    all_jobs: List[Dict] = []
    sources_used: List[str] = []
    for r in sources:
        if isinstance(r, list) and r:
            all_jobs.extend(r)
            src = r[0].get("source", "")
            if src and src not in sources_used:
                sources_used.append(src)

    # Deduplicate
    seen: set = set()
    unique: List[Dict] = []
    for job in all_jobs:
        key = (job.get("title","")[:40].lower(), job.get("company","")[:20].lower())
        if key not in seen:
            seen.add(key)
            unique.append(job)

    scored = _rank_and_score(unique, profile, market)[:max_results]
    mi     = _analyze_market_intelligence(unique, market)

    return {
        "jobs": scored,
        "market": market,
        "total_found": len(unique),
        "sources_used": sources_used or ["Mock"],
        "market_intelligence": mi,
        "source": "live",
        "fetched_at": datetime.utcnow().isoformat(),
    }


async def invalidate_user_cache(user_id: Any, redis_client=None) -> None:
    """Call this after resume update to force fresh job recommendations."""
    if redis_client:
        for market in ("US", "IN"):
            try:
                await redis_client.delete(f"jobs:{user_id}:{market}")
            except Exception:
                pass
