"""
Async circuit breaker — Phase 7

Prevents cascading failures when external services (Adzuna, LLM APIs)
are degraded. Implements the standard three-state machine:

  CLOSED   → normal operation; failures counted
  OPEN     → fast-fail all requests; waits reset_timeout seconds
  HALF_OPEN→ one probe request allowed; success closes, failure re-opens

Usage:
  from .middleware.circuit_breaker import adzuna_breaker, anthropic_breaker

  async with adzuna_breaker:
      jobs = await fetch_adzuna_jobs(...)

  # Or use the decorator:
  @adzuna_breaker.guard
  async def fetch_jobs():
      ...

On CircuitOpenError, return a cached/default response rather than
propagating a 500 to the user:

  try:
      async with adzuna_breaker:
          jobs = await fetch_adzuna_jobs(...)
  except CircuitOpenError:
      jobs = cached_jobs or []

Prometheus integration:
  circuit_breaker_open{service="adzuna"} — 1 if open, 0 if closed
"""
import asyncio
import logging
import time
from enum import Enum
from functools import wraps
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    CLOSED    = "closed"
    OPEN      = "open"
    HALF_OPEN = "half_open"


class CircuitOpenError(Exception):
    """Raised when a circuit breaker is open and a call is attempted."""

    def __init__(self, service: str, retry_after_s: float = 0):
        super().__init__(
            f"Circuit breaker OPEN for '{service}' — "
            f"retry after {retry_after_s:.0f}s"
        )
        self.service        = service
        self.retry_after_s  = retry_after_s


class CircuitBreaker:
    """
    Async-safe circuit breaker.

    All state mutations are serialised through an asyncio.Lock so the
    breaker is safe to share across uvicorn workers within the same process.

    Args:
        service:           Human-readable name used in logs and metrics.
        failure_threshold: Consecutive failures before opening (default 5).
        reset_timeout:     Seconds in OPEN state before probing (default 60).
        success_threshold: Consecutive successes in HALF_OPEN to re-close (default 2).
    """

    def __init__(
        self,
        service:           str,
        failure_threshold: int   = 5,
        reset_timeout:     float = 60.0,
        success_threshold: int   = 2,
    ):
        self.service           = service
        self.failure_threshold = failure_threshold
        self.reset_timeout     = reset_timeout
        self.success_threshold = success_threshold

        self._state:         CircuitState   = CircuitState.CLOSED
        self._failure_count: int            = 0
        self._success_count: int            = 0
        self._opened_at:     Optional[float] = None
        self._lock                          = asyncio.Lock()

    # ── Public properties ──────────────────────────────────────────────────

    @property
    def state(self) -> CircuitState:
        return self._state

    @property
    def is_open(self) -> bool:
        return self._state == CircuitState.OPEN

    @property
    def retry_after_s(self) -> float:
        if self._opened_at is None:
            return 0.0
        elapsed = time.monotonic() - self._opened_at
        return max(0.0, self.reset_timeout - elapsed)

    def stats(self) -> dict:
        return {
            "service":       self.service,
            "state":         self._state.value,
            "failures":      self._failure_count,
            "successes":     self._success_count,
            "retry_after_s": round(self.retry_after_s, 1),
        }

    # ── Context manager ────────────────────────────────────────────────────

    async def __aenter__(self):
        async with self._lock:
            if self._state == CircuitState.OPEN:
                elapsed = time.monotonic() - self._opened_at
                if elapsed >= self.reset_timeout:
                    self._transition(CircuitState.HALF_OPEN)
                    self._success_count = 0
                else:
                    raise CircuitOpenError(self.service, self.reset_timeout - elapsed)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is CircuitOpenError:
            return False  # let it propagate, don't touch state

        async with self._lock:
            if exc_type is not None:
                # A real failure
                self._failure_count += 1
                self._success_count  = 0

                if (
                    self._state == CircuitState.HALF_OPEN
                    or self._failure_count >= self.failure_threshold
                ):
                    self._transition(CircuitState.OPEN)
                    self._opened_at = time.monotonic()
                    logger.error(
                        "Circuit breaker OPENED — service='%s' failures=%d",
                        self.service, self._failure_count,
                    )
                    self._set_metric(1)
            else:
                # Success
                self._failure_count = 0
                if self._state == CircuitState.HALF_OPEN:
                    self._success_count += 1
                    if self._success_count >= self.success_threshold:
                        self._transition(CircuitState.CLOSED)
                        logger.info(
                            "Circuit breaker CLOSED — service='%s' recovered",
                            self.service,
                        )
                        self._set_metric(0)

        return False  # never suppress exceptions

    # ── Decorator ─────────────────────────────────────────────────────────

    def guard(self, func: Callable) -> Callable:
        """Decorator — wraps an async function with this circuit breaker."""
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            async with self:
                return await func(*args, **kwargs)
        return wrapper

    # ── Internal helpers ──────────────────────────────────────────────────

    def _transition(self, new_state: CircuitState) -> None:
        old = self._state.value
        self._state = new_state
        logger.info(
            "Circuit breaker '%s': %s → %s",
            self.service, old, new_state.value,
        )

    def _set_metric(self, value: int) -> None:
        try:
            from ..metrics import CIRCUIT_BREAKER_STATE
            CIRCUIT_BREAKER_STATE.labels(service=self.service).set(value)
        except Exception:
            pass  # metrics optional


# ── Pre-built breakers for each external dependency ────────────────────────
# Import and use these in service/agent code:
#   from backend.app.middleware.circuit_breaker import adzuna_breaker

adzuna_breaker    = CircuitBreaker("adzuna",    failure_threshold=5, reset_timeout=60)
anthropic_breaker = CircuitBreaker("anthropic", failure_threshold=3, reset_timeout=120)
openai_breaker    = CircuitBreaker("openai",    failure_threshold=3, reset_timeout=120)
