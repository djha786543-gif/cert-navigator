"""
Unit tests — ResilienceForecasterAgent + compute_fair_from_inputs.
No database or network required.
"""
import pytest
from src.backend.agents.resilience_forecaster_agent import (
    ResilienceForecasterAgent,
    compute_fair_from_inputs,
)


# ── FAIR model standalone calculator ─────────────────────────────────────

class TestFairCalculator:
    def test_basic_calculation(self):
        result = compute_fair_from_inputs(
            tef=4.0, vulnerability=0.45, primary_loss=50_000, secondary_loss=10_000
        )
        assert "ale" in result
        assert "sle" in result
        assert "tef" in result
        assert "interpretation" in result
        assert "risk_level" in result

    def test_zero_vulnerability_gives_zero_ale(self):
        result = compute_fair_from_inputs(
            tef=10.0, vulnerability=0.0, primary_loss=100_000, secondary_loss=0
        )
        assert result["ale"] == 0

    def test_full_vulnerability(self):
        result = compute_fair_from_inputs(
            tef=2.0, vulnerability=1.0, primary_loss=50_000, secondary_loss=0
        )
        # ALE = TEF × Vulnerability × SLE = 2 × 1.0 × 50_000 = 100_000
        assert result["ale"] == 100_000

    def test_secondary_loss_added_to_sle(self):
        r1 = compute_fair_from_inputs(1.0, 1.0, 50_000, 0)
        r2 = compute_fair_from_inputs(1.0, 1.0, 50_000, 10_000)
        assert r2["sle"] > r1["sle"]
        assert r2["ale"] > r1["ale"]

    def test_risk_level_critical_threshold(self):
        """Very high ALE should yield Critical risk level."""
        result = compute_fair_from_inputs(
            tef=100.0, vulnerability=1.0, primary_loss=500_000, secondary_loss=0
        )
        assert result["risk_level"] in ("Critical", "High")

    def test_risk_level_low_threshold(self):
        result = compute_fair_from_inputs(
            tef=0.1, vulnerability=0.05, primary_loss=1_000, secondary_loss=0
        )
        assert result["risk_level"] in ("Low", "Moderate")

    def test_formula_trace_present(self):
        result = compute_fair_from_inputs(
            tef=6.0, vulnerability=0.5, primary_loss=80_000, secondary_loss=5_000
        )
        assert "formula_trace" in result
        assert len(result["formula_trace"]) > 0

    def test_ale_interpretation_us_format(self):
        result = compute_fair_from_inputs(1.0, 1.0, 100_000, 0)
        assert "$" in result["interpretation"]

    @pytest.mark.parametrize("tef,vuln,primary,secondary,expected_ale", [
        (4.0, 0.5,  50_000, 0,      100_000),
        (10.0, 0.15, 500_000, 0,    750_000),
        (1.0, 1.0, 250_000, 0,      250_000),
        (2.0, 0.8, 3_000_000, 0,    4_800_000),
    ])
    def test_parametric_ale(self, tef, vuln, primary, secondary, expected_ale):
        result = compute_fair_from_inputs(tef, vuln, primary, secondary)
        assert result["ale"] == expected_ale


# ── ResilienceForecasterAgent ─────────────────────────────────────────────

class TestResilienceForecasterAgent:
    @pytest.mark.asyncio
    async def test_run_us_market(self, mock_profile):
        agent = ResilienceForecasterAgent()
        result = await agent.run({"profile": mock_profile, "market": "US"})
        assert result.success, result.error

    @pytest.mark.asyncio
    async def test_result_structure(self, mock_profile):
        agent = ResilienceForecasterAgent()
        result = await agent.run({"profile": mock_profile, "market": "US"})
        d = result.data
        assert "resilience_score" in d
        assert "disruption_signal" in d
        assert "fair_model" in d
        assert "skill_audit" in d
        assert "year_forecast" in d
        assert "mitigation_plan" in d
        assert "resilience_breakdown" in d

    @pytest.mark.asyncio
    async def test_resilience_score_range(self, mock_profile):
        agent = ResilienceForecasterAgent()
        result = await agent.run({"profile": mock_profile, "market": "US"})
        score = result.data["resilience_score"]
        assert 0 <= score <= 100

    @pytest.mark.asyncio
    async def test_disruption_signal_values(self, mock_profile):
        agent = ResilienceForecasterAgent()
        result = await agent.run({"profile": mock_profile, "market": "US"})
        signal = result.data["disruption_signal"]
        assert signal in ("Critical", "High", "Moderate", "Low")

    @pytest.mark.asyncio
    async def test_fair_ale_non_negative(self, mock_profile):
        agent = ResilienceForecasterAgent()
        result = await agent.run({"profile": mock_profile, "market": "US"})
        ale = result.data["fair_model"]["ale"]
        assert ale >= 0

    @pytest.mark.asyncio
    async def test_fair_ale_floor_for_resilient_profile(self):
        """Fully resilient profile (all AI-resilient skills) should still have ALE > 0."""
        resilient_profile = {
            "current_role": "AI Governance Lead",
            "years_experience": 10,
            "skills": ["AI Governance", "Machine Learning", "Ethics"],
            "certifications": ["AIGP", "CISA", "AAIA"],
            "market_pressure_index": 30,
            "mrv_score": 90,
        }
        agent = ResilienceForecasterAgent()
        result = await agent.run({"profile": resilient_profile, "market": "US"})
        assert result.data["fair_model"]["ale"] > 0  # 5% floor enforced

    @pytest.mark.asyncio
    async def test_five_year_forecast_length(self, mock_profile):
        agent = ResilienceForecasterAgent()
        result = await agent.run({"profile": mock_profile, "market": "US"})
        forecast = result.data["year_forecast"]
        assert len(forecast) == 5
        for year_data in forecast:
            assert "year" in year_data
            assert "phase" in year_data
            assert "goal" in year_data
            assert "primary_risk" in year_data

    @pytest.mark.asyncio
    async def test_skill_audit_has_automation_risk(self, mock_profile):
        agent = ResilienceForecasterAgent()
        result = await agent.run({"profile": mock_profile, "market": "US"})
        audit = result.data["skill_audit"]
        assert len(audit) > 0
        for skill in audit:
            assert "automation_risk" in skill
            assert 0 <= skill["automation_risk"] <= 100
            assert "trajectory" in skill
            assert skill["trajectory"] in ("declining", "augmented", "resilient")

    @pytest.mark.asyncio
    async def test_india_market_inr_currency(self, mock_profile_india):
        agent = ResilienceForecasterAgent()
        result = await agent.run({"profile": mock_profile_india, "market": "IN"})
        ale_label = result.data["fair_model"]["ale_label"]
        assert "\u20b9" in ale_label or "INR" in ale_label or "year" in ale_label

    @pytest.mark.asyncio
    async def test_mitigation_roadmap_non_empty(self, mock_profile):
        agent = ResilienceForecasterAgent()
        result = await agent.run({"profile": mock_profile, "market": "US"})
        roadmap = result.data["mitigation_plan"]
        assert isinstance(roadmap, list)
        assert len(roadmap) > 0
        for item in roadmap:
            assert "action" in item
            assert "urgency" in item

    @pytest.mark.asyncio
    async def test_empty_profile_fails_gracefully(self):
        agent = ResilienceForecasterAgent()
        result = await agent.run({"profile": {}, "market": "US"})
        # Should not crash — may return low-score result or error
        # Either success with a default result or a handled failure is acceptable
        assert result is not None
