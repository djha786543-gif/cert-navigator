"""Add user_skills and role_requirements tables

Revision ID: 002_skills_gap_tables
Revises: 001_initial
Create Date: 2026-03-03 00:01:00
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision: str = "002_skills_gap_tables"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_skills",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("skill_name", sa.String(length=120), nullable=False),
        sa.Column("proficiency", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("evidence_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "skill_name", name="uq_user_skills_user_skill"),
        sa.CheckConstraint("proficiency >= 0.0 AND proficiency <= 1.0", name="ck_user_skills_proficiency_0_1"),
        sa.CheckConstraint("evidence_count >= 0", name="ck_user_skills_evidence_non_negative"),
    )
    op.create_index("ix_user_skills_id", "user_skills", ["id"])
    op.create_index("ix_user_skills_user_id", "user_skills", ["user_id"])
    op.create_index("ix_user_skills_user_skill", "user_skills", ["user_id", "skill_name"])

    op.create_table(
        "role_requirements",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("role_key", sa.String(length=120), nullable=False),
        sa.Column("market", sa.String(length=10), nullable=False, server_default="US"),
        sa.Column("skill_name", sa.String(length=120), nullable=False),
        sa.Column("required_level", sa.Float(), nullable=False, server_default="0.7"),
        sa.Column("importance_weight", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("market_demand_score", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("baseline_learning_hours", sa.Integer(), nullable=False, server_default="20"),
        sa.Column("is_critical", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("role_key", "market", "skill_name", name="uq_role_requirements_role_market_skill"),
        sa.CheckConstraint("required_level >= 0.0 AND required_level <= 1.0", name="ck_role_req_required_0_1"),
        sa.CheckConstraint("importance_weight > 0.0", name="ck_role_req_importance_positive"),
        sa.CheckConstraint("market_demand_score >= 0.0 AND market_demand_score <= 1.0", name="ck_role_req_demand_0_1"),
        sa.CheckConstraint("baseline_learning_hours >= 0", name="ck_role_req_learning_hours_non_negative"),
    )
    op.create_index("ix_role_requirements_id", "role_requirements", ["id"])
    op.create_index("ix_role_requirements_role_key", "role_requirements", ["role_key"])
    op.create_index("ix_role_requirements_market", "role_requirements", ["market"])
    op.create_index("ix_role_requirements_role_market", "role_requirements", ["role_key", "market"])


def downgrade() -> None:
    op.drop_index("ix_role_requirements_role_market", table_name="role_requirements")
    op.drop_index("ix_role_requirements_market", table_name="role_requirements")
    op.drop_index("ix_role_requirements_role_key", table_name="role_requirements")
    op.drop_index("ix_role_requirements_id", table_name="role_requirements")
    op.drop_table("role_requirements")

    op.drop_index("ix_user_skills_user_skill", table_name="user_skills")
    op.drop_index("ix_user_skills_user_id", table_name="user_skills")
    op.drop_index("ix_user_skills_id", table_name="user_skills")
    op.drop_table("user_skills")
