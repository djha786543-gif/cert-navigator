"""
Agent Registry — the central dispatcher for all Career Navigator agents.

Role: Decides whether an agent runs inline (FastAPI handler) or via
Celery queue based on its resource_tier.

  LIGHT  → inline, no queue
  MEDIUM → inline with 10s timeout, falls back to Celery on timeout
  HEAVY  → always routes to Celery (never blocks the web server)

This is the architectural boundary between Window 2 (Web API) and
Window 3 (Background Worker). All Phase 3+ heavy agents go through here.

Current agent roster:
  Phase 1:  ResumeInferenceAgent    (MEDIUM)
  Phase 2:  MarketIntelligenceAgent (MEDIUM) — stub, built in Phase 2
  Phase 3:  ArtifactSovereignAgent  (HEAVY)  — stub, built in Phase 3
  Phase 4:  ResilienceForecaster    (MEDIUM) — stub, built in Phase 4
  Phase 5:  ProctorAgent            (HEAVY)  — stub, built in Phase 5
"""
import asyncio
import logging
from typing import Any, Dict, Optional, Type

from .base_agent import AgentResult, BaseAgent, CapacityExceededError, ResourceTier
from .resume_inference_agent import ResumeInferenceAgent
from .market_intelligence_agent import MarketIntelligenceAgent
from .artifact_sovereign_agent import ArtifactSovereignAgent
from .resilience_forecaster_agent import ResilienceForecasterAgent
from .proctor_agent import ProctorAgent
from .universal_architect_agent import UniversalArchitectAgent

logger = logging.getLogger(__name__)


# ── Registry ───────────────────────────────────────────────────────────────
_REGISTRY: Dict[str, BaseAgent] = {
    "resume_inference":      ResumeInferenceAgent(),
    "market_intelligence":   MarketIntelligenceAgent(),
    "artifact_sovereign":    ArtifactSovereignAgent(),
    "resilience_forecaster": ResilienceForecasterAgent(),
    "proctor":               ProctorAgent(),
    "universal_architect":   UniversalArchitectAgent(),
}

INLINE_TIMEOUT_SECONDS = 10  # MEDIUM agents have 10s before falling back


async def dispatch(agent_name: str, input_data: Dict[str, Any]) -> AgentResult:
    """
    Main dispatch function.

    - LIGHT/MEDIUM agents: run inline (async)
    - HEAVY agents: route to Celery and return task_id immediately
    - MEDIUM agents that timeout: fall back to Celery

    Usage:
        result = await dispatch("resume_inference", {"profile": profile_dict})
    """
    agent = _REGISTRY.get(agent_name)
    if not agent:
        return AgentResult(
            success=False,
            error=f"Unknown agent: {agent_name}",
            agent_name=agent_name,
        )

    # Heavy agents always use Celery
    if agent.resource_tier == ResourceTier.HEAVY:
        return await _dispatch_to_celery(agent_name, input_data)

    # Light/Medium agents run inline
    try:
        if agent.resource_tier == ResourceTier.MEDIUM:
            result = await asyncio.wait_for(
                agent.run(input_data),
                timeout=INLINE_TIMEOUT_SECONDS,
            )
        else:
            result = await agent.run(input_data)
        return result

    except asyncio.TimeoutError:
        logger.warning(
            "[%s] Inline timeout after %ds — falling back to Celery",
            agent_name, INLINE_TIMEOUT_SECONDS,
        )
        return await _dispatch_to_celery(agent_name, input_data)

    except CapacityExceededError as exc:
        logger.error("[%s] Capacity exceeded: %s", agent_name, exc)
        result = AgentResult(success=False, error=str(exc), agent_name=agent_name)
        result.flag(str(exc), exc.migrate_to)
        return result


async def _dispatch_to_celery(
    agent_name: str, input_data: Dict[str, Any]
) -> AgentResult:
    """
    Route agent execution to Celery background queue.
    Returns immediately with a task_id for polling.

    ⚠️ CAPACITY FLAG: Celery with concurrency=2 handles 2 heavy agents
    simultaneously. Task #3 waits ~30s. For burst > 10 tasks/minute:
    scale to AWS Lambda or increase worker concurrency.
    """
    try:
        from .workers.tasks import run_agent_task  # noqa: circular-safe
        task = run_agent_task.delay(agent_name, input_data)
        return AgentResult(
            success=True,
            data={
                "queued": True,
                "task_id": task.id,
                "poll_url": f"/api/agents/task/{task.id}",
                "note": f"Agent '{agent_name}' queued. Poll poll_url for result.",
            },
            agent_name=agent_name,
        )
    except Exception as exc:
        logger.error("Celery dispatch failed: %s", exc)
        return AgentResult(
            success=False,
            error=f"Queue unavailable: {exc}",
            agent_name=agent_name,
        )


def list_agents() -> Dict[str, str]:
    """Return all registered agents with their resource tier."""
    return {name: agent.resource_tier.value for name, agent in _REGISTRY.items()}
