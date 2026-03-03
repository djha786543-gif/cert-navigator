"""Align role_requirements fields to Skills Gap Analyzer v2.

Revision ID: 003_skills_gap_v2_alignment
Revises: 002_skills_gap_tables
Create Date: 2026-03-03 01:25:00
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision: str = "003_skills_gap_v2_alignment"
down_revision: Union[str, None] = "002_skills_gap_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    column_names = {col["name"] for col in inspector.get_columns("role_requirements")}

    if "demand_multiplier" not in column_names:
        op.add_column(
            "role_requirements",
            sa.Column("demand_multiplier", sa.Float(), nullable=False, server_default="0.5"),
        )

        if "market_demand_score" in column_names:
            op.execute(
                sa.text(
                    """
                    UPDATE role_requirements
                    SET demand_multiplier = market_demand_score
                    WHERE market_demand_score IS NOT NULL
                    """
                )
            )

    with op.batch_alter_table("role_requirements") as batch_op:
        try:
            batch_op.drop_constraint("ck_role_req_importance_positive", type_="check")
        except Exception:
            pass

        try:
            batch_op.drop_constraint("ck_role_req_importance_0_1", type_="check")
        except Exception:
            pass

        try:
            batch_op.drop_constraint("ck_role_req_demand_0_1", type_="check")
        except Exception:
            pass

        batch_op.create_check_constraint(
            "ck_role_req_importance_0_1",
            "importance_weight >= 0.0 AND importance_weight <= 1.0",
        )
        batch_op.create_check_constraint(
            "ck_role_req_demand_0_1",
            "demand_multiplier >= 0.0 AND demand_multiplier <= 1.0",
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    column_names = {col["name"] for col in inspector.get_columns("role_requirements")}

    with op.batch_alter_table("role_requirements") as batch_op:
        try:
            batch_op.drop_constraint("ck_role_req_importance_0_1", type_="check")
        except Exception:
            pass

        try:
            batch_op.drop_constraint("ck_role_req_demand_0_1", type_="check")
        except Exception:
            pass

        batch_op.create_check_constraint(
            "ck_role_req_importance_positive",
            "importance_weight > 0.0",
        )

        if "market_demand_score" in column_names:
            batch_op.create_check_constraint(
                "ck_role_req_demand_0_1",
                "market_demand_score >= 0.0 AND market_demand_score <= 1.0",
            )

    if "demand_multiplier" in column_names:
        op.drop_column("role_requirements", "demand_multiplier")
