"""
ORM models for production skills-gap analysis.

These tables are normalized so the analyzer can operate on typed, auditable
data instead of ad-hoc JSON blobs.
"""
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class UserSkill(Base):
    __tablename__ = "user_skills"

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        sa.Integer,
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    skill_name: Mapped[str] = mapped_column(sa.String(120), nullable=False)
    proficiency: Mapped[float] = mapped_column(
        sa.Float,
        nullable=False,
        server_default="0.0",
    )
    evidence_count: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
        server_default="0",
    )
    last_used_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True),
        onupdate=sa.func.now(),
    )

    __table_args__ = (
        sa.UniqueConstraint("user_id", "skill_name", name="uq_user_skills_user_skill"),
        sa.CheckConstraint("proficiency >= 0.0 AND proficiency <= 1.0", name="ck_user_skills_proficiency_0_1"),
        sa.CheckConstraint("evidence_count >= 0", name="ck_user_skills_evidence_non_negative"),
        sa.Index("ix_user_skills_user_skill", "user_id", "skill_name"),
    )


class RoleRequirement(Base):
    __tablename__ = "role_requirements"

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True, index=True)
    role_key: Mapped[str] = mapped_column(sa.String(120), nullable=False, index=True)
    market: Mapped[str] = mapped_column(
        sa.String(10),
        nullable=False,
        server_default="US",
        index=True,
    )
    skill_name: Mapped[str] = mapped_column(sa.String(120), nullable=False)
    required_level: Mapped[float] = mapped_column(
        sa.Float,
        nullable=False,
        server_default="0.7",
    )
    importance_weight: Mapped[float] = mapped_column(
        sa.Float,
        nullable=False,
        server_default="1.0",
    )
    demand_multiplier: Mapped[float] = mapped_column(
        sa.Float,
        nullable=False,
        server_default="0.5",
    )
    baseline_learning_hours: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
        server_default="20",
    )
    is_critical: Mapped[bool] = mapped_column(
        sa.Boolean,
        nullable=False,
        server_default="false",
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True),
        onupdate=sa.func.now(),
    )

    __table_args__ = (
        sa.UniqueConstraint("role_key", "market", "skill_name", name="uq_role_requirements_role_market_skill"),
        sa.CheckConstraint("required_level >= 0.0 AND required_level <= 1.0", name="ck_role_req_required_0_1"),
        sa.CheckConstraint("importance_weight >= 0.0 AND importance_weight <= 1.0", name="ck_role_req_importance_0_1"),
        sa.CheckConstraint("demand_multiplier >= 0.0 AND demand_multiplier <= 1.0", name="ck_role_req_demand_0_1"),
        sa.CheckConstraint("baseline_learning_hours >= 0", name="ck_role_req_learning_hours_non_negative"),
        sa.Index("ix_role_requirements_role_market", "role_key", "market"),
    )
