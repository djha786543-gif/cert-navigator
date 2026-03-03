from __future__ import annotations

from datetime import datetime, timezone

from backend.app.schemas.skills_gap import RoleRequirementRecord, UserSkillRecord
from backend.app.services.skills_gap_service import SkillsGapService


FIXED_NOW = datetime(2026, 3, 3, tzinfo=timezone.utc)


def _user_skill(
    name: str,
    proficiency: float,
    evidence_count: int = 5,
    last_used_at: datetime | None = FIXED_NOW,
) -> UserSkillRecord:
    return UserSkillRecord(
        skill_name=name,
        proficiency=proficiency,
        evidence_count=evidence_count,
        last_used_at=last_used_at,
    )


def _requirement(
    name: str,
    required_level: float,
    importance_weight: float,
    demand_multiplier: float,
    baseline_learning_hours: int,
    is_critical: bool = False,
) -> RoleRequirementRecord:
    return RoleRequirementRecord(
        skill_name=name,
        role_key="cloud-security-engineer",
        market="US",
        required_level=required_level,
        importance_weight=importance_weight,
        demand_multiplier=demand_multiplier,
        baseline_learning_hours=baseline_learning_hours,
        is_critical=is_critical,
    )


def test_full_coverage_case() -> None:
    service = SkillsGapService(now=FIXED_NOW)
    user_skills = [
        _user_skill("python", 0.90),
        _user_skill("sql", 0.85),
    ]
    requirements = [
        _requirement("python", 0.80, 0.90, 0.80, 20),
        _requirement("sql", 0.70, 0.75, 0.60, 12),
    ]

    scored = service._score_gaps(user_skills=user_skills, requirements=requirements)
    confidence = service._compute_confidence(
        user_skills=user_skills,
        requirements=requirements,
        scored_gaps=scored,
    )

    assert scored == []
    assert round(confidence, 4) == 0.95


def test_zero_coverage_case() -> None:
    service = SkillsGapService(now=FIXED_NOW)
    user_skills: list[UserSkillRecord] = []
    requirements = [
        _requirement("kubernetes", 0.80, 0.90, 1.00, 30),
    ]

    scored = service._score_gaps(user_skills=user_skills, requirements=requirements)
    confidence = service._compute_confidence(
        user_skills=user_skills,
        requirements=requirements,
        scored_gaps=scored,
    )

    assert len(scored) == 1
    assert scored[0].skill_id == "kubernetes"
    assert round(confidence, 4) == 0.2


def test_partial_gaps_and_priority_order() -> None:
    service = SkillsGapService(now=FIXED_NOW)
    user_skills = [
        _user_skill("python", 0.40),
        _user_skill("sql", 0.90),
    ]
    requirements = [
        _requirement("python", 0.90, 1.00, 1.00, 10),
        _requirement("sql", 0.80, 1.00, 1.00, 10),
        _requirement("terraform", 0.70, 0.80, 0.50, 20),
    ]

    scored = service._score_gaps(user_skills=user_skills, requirements=requirements)
    scored.sort(key=lambda item: item.priority_score, reverse=True)

    assert [item.skill_id for item in scored] == ["python", "terraform"]
    assert round(scored[0].gap, 4) == 0.5
    assert round(scored[0].priority_score, 4) == 0.5
    assert scored[0].estimated_learning_hours == 5
    assert round(scored[1].gap, 4) == 0.7
    assert round(scored[1].priority_score, 4) == 0.28
    assert scored[1].estimated_learning_hours == 7


def test_confidence_bounds() -> None:
    service = SkillsGapService(now=FIXED_NOW)
    user_skills = [_user_skill("python", 1.0)]
    requirements = [_requirement("python", 1.0, 1.0, 1.0, 1)]

    scored = service._score_gaps(user_skills=user_skills, requirements=requirements)
    confidence = service._compute_confidence(
        user_skills=user_skills,
        requirements=requirements,
        scored_gaps=scored,
    )

    assert 0.0 <= confidence <= 1.0
    assert service._bound(-3.0) == 0.0
    assert service._bound(3.0) == 1.0


def test_decay_half_life_behavior() -> None:
    service = SkillsGapService(now=FIXED_NOW)

    now_decay = service._decay(FIXED_NOW)
    twelve_months = service._decay(datetime(2025, 3, 3, tzinfo=timezone.utc))
    twenty_four_months = service._decay(datetime(2024, 3, 3, tzinfo=timezone.utc))
    unknown = service._decay(None)

    assert round(now_decay, 4) == 1.0
    assert abs(twelve_months - 0.5) < 0.01
    assert abs(twenty_four_months - 0.25) < 0.01
    assert unknown == 0.0
