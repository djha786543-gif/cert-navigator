"""
Pytest fixtures shared across all test modules.

Design:
  Unit tests (tests/unit/) — pure Python, no DB, no network, no real auth.
  Integration tests (tests/integration/) — require Docker services running.

Fixtures:
  mock_profile   — sample user profile dict (from data/sample_resume.json)
  proctor_session — a live Practice session for AIGP (10 questions)
"""
import json
import os
import sys

import pytest

# ── Path setup ────────────────────────────────────────────────────────────
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)


# ── Sample profile fixture ────────────────────────────────────────────────
@pytest.fixture
def mock_profile():
    """Minimal IT Audit profile for agent testing."""
    return {
        "name": "DJ Test",
        "email": "dj@test.com",
        "current_role": "IT Audit Manager",
        "years_experience": 8,
        "skills": [
            "SOX Compliance",
            "IT General Controls",
            "Risk Assessment",
            "CISA",
            "Data Analytics",
            "Python",
            "SQL",
            "Internal Audit",
        ],
        "certifications": ["CISA"],
        "education": "MBA, Information Systems",
        "market_pressure_index": 62,
        "mrv_score": 71,
        "location": "Los Angeles, CA",
        "target_role": "AI Governance Lead",
    }


@pytest.fixture
def mock_profile_india(mock_profile):
    """Profile variant for India market testing."""
    p = dict(mock_profile)
    p["location"] = "Bangalore, India"
    return p


@pytest.fixture
def proctor_session():
    """A live AIGP practice session (10 questions, no timer)."""
    from src.backend.agents.proctor_agent import create_session
    session = create_session("aigp", "practice", "pytest_user")
    yield session
    # Cleanup: sessions auto-expire, no explicit teardown needed
