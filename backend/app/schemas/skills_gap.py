"""Pydantic v2 schemas for Skills Gap Analyzer v2 artifact calculations."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class SkillsGapRequest(BaseModel):
    role_key: str = Field(min_length=1, max_length=120)
    market: str = Field(default="US", min_length=2, max_length=10)

    @field_validator("role_key")
    @classmethod
    def role_key_normalized(cls, value: str) -> str:
        return value.strip()

    @field_validator("market")
    @classmethod
    def market_normalized(cls, value: str) -> str:
        return value.strip().upper()


class UserSkillRecord(BaseModel):
    skill_name: str
    proficiency: float = Field(ge=0.0, le=1.0)
    evidence_count: int = Field(ge=0)
    last_used_at: datetime | None = None

    model_config = {"from_attributes": True}


class RoleRequirementRecord(BaseModel):
    skill_name: str
    role_key: str
    market: str
    required_level: float = Field(ge=0.0, le=1.0)
    importance_weight: float = Field(ge=0.0, le=1.0)
    demand_multiplier: float = Field(ge=0.0, le=1.0)
    baseline_learning_hours: int = Field(ge=0)
    is_critical: bool = False

    model_config = {"from_attributes": True}


class MissingSkill(BaseModel):
    skill_id: str
    gap: float = Field(ge=0.0, le=1.0)
    priority_score: float = Field(ge=0.0)
    estimated_learning_hours: int = Field(ge=0)


class SkillsGapAnalysisResponse(BaseModel):
    missing_skills: list[MissingSkill]
    priority_order: list[str]
    estimated_learning_hours: int = Field(ge=0)
    confidence_score: float = Field(ge=0.0, le=1.0)
