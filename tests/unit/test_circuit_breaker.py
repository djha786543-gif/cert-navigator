"""
Unit tests — CircuitBreaker middleware (Phase 7)
No external services required.
"""
import asyncio
import pytest
from backend.app.middleware.circuit_breaker import (
    CircuitBreaker,
    CircuitOpenError,
    CircuitState,
)


# ── Helpers ────────────────────────────────────────────────────────────────

async def _succeed(breaker: CircuitBreaker) -> str:
    async with breaker:
        return "ok"


async def _fail(breaker: CircuitBreaker) -> None:
    async with breaker:
        raise RuntimeError("simulated failure")


# ── State transitions ──────────────────────────────────────────────────────

class TestCircuitBreakerStates:

    def test_initial_state_is_closed(self):
        cb = CircuitBreaker("test")
        assert cb.state == CircuitState.CLOSED
        assert not cb.is_open

    @pytest.mark.asyncio
    async def test_success_keeps_closed(self):
        cb = CircuitBreaker("test")
        await _succeed(cb)
        assert cb.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_opens_after_threshold_failures(self):
        cb = CircuitBreaker("test", failure_threshold=3)
        for _ in range(3):
            with pytest.raises(RuntimeError):
                await _fail(cb)
        assert cb.state == CircuitState.OPEN
        assert cb.is_open

    @pytest.mark.asyncio
    async def test_stays_closed_below_threshold(self):
        cb = CircuitBreaker("test", failure_threshold=5)
        for _ in range(4):
            with pytest.raises(RuntimeError):
                await _fail(cb)
        assert cb.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_open_raises_circuit_open_error(self):
        cb = CircuitBreaker("svc", failure_threshold=1)
        with pytest.raises(RuntimeError):
            await _fail(cb)
        assert cb.is_open

        with pytest.raises(CircuitOpenError) as exc_info:
            await _succeed(cb)
        assert "svc" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_transitions_to_half_open_after_reset_timeout(self):
        cb = CircuitBreaker("test", failure_threshold=1, reset_timeout=0.05)
        with pytest.raises(RuntimeError):
            await _fail(cb)
        assert cb.is_open

        await asyncio.sleep(0.1)  # wait for reset timeout
        # Next call should be allowed (HALF_OPEN probe)
        result = await _succeed(cb)
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_closes_after_success_threshold_in_half_open(self):
        cb = CircuitBreaker("test", failure_threshold=1, reset_timeout=0.05, success_threshold=2)
        with pytest.raises(RuntimeError):
            await _fail(cb)
        await asyncio.sleep(0.1)

        # First probe — still HALF_OPEN after 1 success (threshold=2)
        await _succeed(cb)
        assert cb.state == CircuitState.HALF_OPEN

        # Second probe — should close now
        await _succeed(cb)
        assert cb.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_reopens_on_failure_in_half_open(self):
        cb = CircuitBreaker("test", failure_threshold=1, reset_timeout=0.05)
        with pytest.raises(RuntimeError):
            await _fail(cb)
        await asyncio.sleep(0.1)

        # Probe fails → re-open
        with pytest.raises(RuntimeError):
            await _fail(cb)
        assert cb.state == CircuitState.OPEN


# ── Stats / properties ─────────────────────────────────────────────────────

class TestCircuitBreakerStats:

    def test_stats_structure(self):
        cb = CircuitBreaker("stats_test")
        s = cb.stats()
        assert "service" in s
        assert "state" in s
        assert "failures" in s
        assert "successes" in s
        assert s["state"] == "closed"

    @pytest.mark.asyncio
    async def test_failure_count_increments(self):
        cb = CircuitBreaker("test", failure_threshold=10)
        for _ in range(3):
            with pytest.raises(RuntimeError):
                await _fail(cb)
        assert cb.stats()["failures"] == 3

    @pytest.mark.asyncio
    async def test_failure_count_resets_on_success(self):
        cb = CircuitBreaker("test", failure_threshold=10)
        with pytest.raises(RuntimeError):
            await _fail(cb)
        assert cb.stats()["failures"] == 1
        await _succeed(cb)
        assert cb.stats()["failures"] == 0

    @pytest.mark.asyncio
    async def test_retry_after_is_positive_when_open(self):
        cb = CircuitBreaker("test", failure_threshold=1, reset_timeout=30)
        with pytest.raises(RuntimeError):
            await _fail(cb)
        assert cb.retry_after_s > 0
        assert cb.retry_after_s <= 30


# ── Decorator ──────────────────────────────────────────────────────────────

class TestCircuitBreakerDecorator:

    @pytest.mark.asyncio
    async def test_guard_decorator_passes_on_success(self):
        cb = CircuitBreaker("deco_test")

        @cb.guard
        async def my_func():
            return "decorated"

        result = await my_func()
        assert result == "decorated"

    @pytest.mark.asyncio
    async def test_guard_decorator_counts_failures(self):
        cb = CircuitBreaker("deco_fail", failure_threshold=10)

        @cb.guard
        async def always_fails():
            raise ValueError("boom")

        for _ in range(3):
            with pytest.raises(ValueError):
                await always_fails()
        assert cb.stats()["failures"] == 3


# ── Pre-built breakers ─────────────────────────────────────────────────────

class TestPrebuiltBreakers:

    def test_adzuna_breaker_exists(self):
        from backend.app.middleware.circuit_breaker import adzuna_breaker
        assert adzuna_breaker.service == "adzuna"
        assert adzuna_breaker.state == CircuitState.CLOSED

    def test_anthropic_breaker_exists(self):
        from backend.app.middleware.circuit_breaker import anthropic_breaker
        assert anthropic_breaker.service == "anthropic"
        assert anthropic_breaker.failure_threshold == 3
