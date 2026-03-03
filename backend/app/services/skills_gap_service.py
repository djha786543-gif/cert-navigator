"""Skills Gap Analyzer v2 service implementation from the canonical artifact."""
from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Final

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.skills_gap import RoleRequirement, UserSkill
from ..schemas.skills_gap import (
    MissingSkill,
    RoleRequirementRecord,
    SkillsGapAnalysisResponse,
    UserSkillRecord,
)


class SkillsGapService:
    """Service that computes v2 gaps, priority, estimated hours, and confidence."""

    # v2 artifact constants
    HALF_LIFE_MONTHS: Final[float] = 12.0
    DAYS_PER_MONTH: Final[float] = 30.0
    CRITICAL_MULTIPLIER_CRITICAL: Final[float] = 1.15
    CRITICAL_MULTIPLIER_DEFAULT: Final[float] = 1.0
    EVIDENCE_NORMALIZER: Final[float] = 5.0

    CONFIDENCE_WEIGHT_COVERAGE: Final[float] = 0.35
    CONFIDENCE_WEIGHT_RECENCY: Final[float] = 0.25
    CONFIDENCE_WEIGHT_EVIDENCE: Final[float] = 0.20
    CONFIDENCE_WEIGHT_ROLE_QUALITY: Final[float] = 0.15
    CONFIDENCE_WEIGHT_GAP_DENSITY: Final[float] = 0.05

    MIN_NORMALIZED: Final[float] = 0.0
    MAX_NORMALIZED: Final[float] = 1.0

    def __init__(self, now: datetime | None = None) -> None:
        # Injected clock makes calculations deterministic in tests.
        self._now = now or datetime.now(timezone.utc)

    async def analyze(
        self,
        db: AsyncSession,
        user_id: int,
        role_key: str,
        market: str = "US",
    ) -> SkillsGapAnalysisResponse:
        normalized_role = role_key.strip()
        normalized_market = market.upper()

        user_skills = await self._fetch_user_skills(db=db, user_id=user_id)
        requirements = await self._fetch_role_requirements(
            db=db,
            role_key=normalized_role,
            market=normalized_market,
        )

        if not requirements:
            return SkillsGapAnalysisResponse(
                missing_skills=[],
                priority_order=[],
                estimated_learning_hours=0,
                confidence_score=0.0,
            )

        scored_gaps = self._score_gaps(user_skills=user_skills, requirements=requirements)
        scored_gaps.sort(key=lambda s: s.priority_score, reverse=True)

        priority_order = [item.skill_id for item in scored_gaps]
        estimated_hours = int(sum(item.estimated_learning_hours for item in scored_gaps))
        confidence = self._compute_confidence(
            user_skills=user_skills,
            requirements=requirements,
            scored_gaps=scored_gaps,
        )

        return SkillsGapAnalysisResponse(
            missing_skills=scored_gaps,
            priority_order=priority_order,
            estimated_learning_hours=estimated_hours,
            confidence_score=round(confidence, 4),
        )

    async def _fetch_user_skills(self, db: AsyncSession, user_id: int) -> list[UserSkillRecord]:
        result = await db.execute(select(UserSkill).where(UserSkill.user_id == user_id))
        rows = result.scalars().all()
        return [UserSkillRecord.model_validate(r) for r in rows]

    async def _fetch_role_requirements(
        self,
        db: AsyncSession,
        role_key: str,
        market: str,
    ) -> list[RoleRequirementRecord]:
        result = await db.execute(
            select(RoleRequirement).where(
                RoleRequirement.role_key == role_key,
                RoleRequirement.market == market,
            )
        )
        rows = result.scalars().all()
        return [RoleRequirementRecord.model_validate(r) for r in rows]

    def _score_gaps(
        self,
        user_skills: list[UserSkillRecord],
        requirements: list[RoleRequirementRecord],
    ) -> list[MissingSkill]:
        """Apply canonical v2 requirement-level scoring formulas."""
        user_map = {self._norm_key(s.skill_name): s for s in user_skills}
        scores: list[MissingSkill] = []

        for req in requirements:
            skill_id = self._norm_key(req.skill_name)
            user_skill = user_map.get(skill_id)

            proficiency = user_skill.proficiency if user_skill else self.MIN_NORMALIZED
            effective_proficiency = proficiency * self._decay(user_skill.last_used_at if user_skill else None)
            gap = max(self.MIN_NORMALIZED, req.required_level - effective_proficiency)

            if gap <= self.MIN_NORMALIZED:
                continue

            critical_multiplier = (
                self.CRITICAL_MULTIPLIER_CRITICAL if req.is_critical else self.CRITICAL_MULTIPLIER_DEFAULT
            )
            priority_score = gap * req.importance_weight * req.demand_multiplier * critical_multiplier
            estimated_learning_hours = math.ceil(
                req.baseline_learning_hours * gap * req.demand_multiplier
            )

            scores.append(
                MissingSkill(
                    skill_id=skill_id,
                    gap=gap,
                    priority_score=priority_score,
                    estimated_learning_hours=max(0, int(estimated_learning_hours)),
                )
            )

        return scores

    def _compute_confidence(
        self,
        user_skills: list[UserSkillRecord],
        requirements: list[RoleRequirementRecord],
        scored_gaps: list[MissingSkill],
    ) -> float:
        """Compute confidence per v2 weighted formula and bound to [0,1]."""
        if not requirements:
            return 0.0

        user_map = {self._norm_key(s.skill_name): s for s in user_skills}
        matched = [r for r in requirements if self._norm_key(r.skill_name) in user_map]

        coverage = len(matched) / len(requirements)

        if matched:
            recency_values = [
                self._decay(user_map[self._norm_key(r.skill_name)].last_used_at)
                for r in matched
            ]
            recency = sum(recency_values) / len(recency_values)

            evidence_values = [
                self._bound(
                    user_map[self._norm_key(r.skill_name)].evidence_count / self.EVIDENCE_NORMALIZER
                )
                for r in matched
            ]
            evidence = sum(evidence_values) / len(evidence_values)
        else:
            recency = self.MIN_NORMALIZED
            evidence = self.MIN_NORMALIZED

        role_quality_flags = [
            1.0
            if (
                self.MIN_NORMALIZED <= r.required_level <= self.MAX_NORMALIZED
                and self.MIN_NORMALIZED <= r.importance_weight <= self.MAX_NORMALIZED
                and self.MIN_NORMALIZED <= r.demand_multiplier <= self.MAX_NORMALIZED
                and r.baseline_learning_hours >= 0
            )
            else 0.0
            for r in requirements
        ]
        role_quality = sum(role_quality_flags) / len(role_quality_flags)

        gap_density = self._bound(len(scored_gaps) / len(requirements))

        confidence = (
            self.CONFIDENCE_WEIGHT_COVERAGE * coverage
            + self.CONFIDENCE_WEIGHT_RECENCY * recency
            + self.CONFIDENCE_WEIGHT_EVIDENCE * evidence
            + self.CONFIDENCE_WEIGHT_ROLE_QUALITY * role_quality
            + self.CONFIDENCE_WEIGHT_GAP_DENSITY * gap_density
        )
        return self._bound(confidence)

    @staticmethod
    def _norm_key(value: str) -> str:
        """Normalize skill identifiers for joins and output `skill_id` values."""
        return " ".join(value.lower().split())

    def _decay(self, last_used_at: datetime | None) -> float:
        """Exponential decay with a 12-month half-life as required by v2 artifact."""
        if last_used_at is None:
            return self.MIN_NORMALIZED

        used_at = last_used_at
        if used_at.tzinfo is None:
            used_at = used_at.replace(tzinfo=timezone.utc)

        days_since = max(0.0, (self._now - used_at).total_seconds() / 86400.0)
        months_since = days_since / self.DAYS_PER_MONTH
        decay = 0.5 ** (months_since / self.HALF_LIFE_MONTHS)
        return self._bound(decay)

    def _bound(self, value: float) -> float:
        return max(self.MIN_NORMALIZED, min(self.MAX_NORMALIZED, value))
