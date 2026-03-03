"""
Base Agent — abstract class for all Career Navigator agents.

Agent design pattern:
  Each agent exposes a single async .run(input) -> AgentResult interface.
  Internally, agents can chain multiple LLM calls, tool calls, and
  vector operations. Results are typed via Pydantic models.

Capacity control:
  - Each agent has a declared resource_tier: "light" | "medium" | "heavy"
  - "heavy" agents (Artifact Sovereign, Bulk Scraper) are routed to Celery
  - "light" and "medium" agents run inline in FastAPI request handlers
  - This is enforced by the AgentRouter (see agent_registry.py)

⚠️ CAPACITY SAFEGUARD PROTOCOL:
  If any agent detects it is exceeding local resource limits, it raises
  CapacityExceededError with a migration recommendation. The API layer
  catches this and returns HTTP 503 with X-Migrate-To header.
"""
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class ResourceTier(str, Enum):
    LIGHT = "light"    # < 500ms, no LLM calls, runs inline
    MEDIUM = "medium"  # 500ms-5s, 1 LLM call, runs inline with timeout
    HEAVY = "heavy"    # > 5s, multiple LLM calls → MUST use Celery queue


@dataclass
class AgentResult:
    success: bool
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    duration_ms: int = 0
    agent_name: str = ""
    capacity_warnings: list = field(default_factory=list)

    def flag(self, warning: str, migrate_to: Optional[str] = None) -> None:
        """Add a capacity warning to the result."""
        msg = f"⚠️ CAPACITY FLAG [{self.agent_name}]: {warning}"
        if migrate_to:
            msg += f" → Migrate to: {migrate_to}"
        self.capacity_warnings.append(msg)
        logger.warning(msg)


class CapacityExceededError(Exception):
    """Raised when an agent detects it would exceed local resource limits."""
    def __init__(self, message: str, migrate_to: str = "AWS Lambda"):
        self.migrate_to = migrate_to
        super().__init__(message)


class BaseAgent(ABC):
    """
    Abstract base class for all Career Navigator agents.

    Subclasses implement:
      - name: str  — unique identifier (used in logs + task routing)
      - resource_tier: ResourceTier  — controls inline vs Celery routing
      - _execute(input_data) → AgentResult  — the core logic
    """

    name: str = "base_agent"
    resource_tier: ResourceTier = ResourceTier.LIGHT
    version: str = "1.0"

    async def run(self, input_data: Dict[str, Any]) -> AgentResult:
        """
        Public entry point. Wraps _execute() with:
          - Timing
          - Capacity tier enforcement
          - Error handling + structured result
        """
        start = time.monotonic()
        result = AgentResult(success=False, agent_name=self.name)

        try:
            result = await self._execute(input_data)
            result.agent_name = self.name
            # Only mark success if _execute() didn't already set an error
            if not result.error:
                result.success = True
        except CapacityExceededError as exc:
            result.error = str(exc)
            result.flag(str(exc), exc.migrate_to)
        except Exception as exc:
            logger.error("[%s] Execution failed: %s", self.name, exc, exc_info=True)
            result.error = str(exc)
        finally:
            result.duration_ms = int((time.monotonic() - start) * 1000)
            logger.info(
                "[%s] completed in %dms | success=%s",
                self.name, result.duration_ms, result.success,
            )

        return result

    @abstractmethod
    async def _execute(self, input_data: Dict[str, Any]) -> AgentResult:
        """Override this in each concrete agent."""
        ...
