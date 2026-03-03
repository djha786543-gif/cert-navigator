"""Initial schema — users table with pgvector skill embedding

Revision ID: 001_initial
Revises:
Create Date: 2025-03-01 00:00:00

Creates:
  - pgvector extension (idempotent)
  - users table with Vector(384) skill_vector column
  - HNSW cosine-similarity index on skill_vector
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

# revision identifiers
revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Enable pgvector extension (idempotent)
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # 2. Create users table
    op.create_table(
        "users",
        sa.Column("id",              sa.Integer(),      primary_key=True, autoincrement=True),
        sa.Column("email",           sa.String(255),    nullable=False),
        sa.Column("hashed_password", sa.String(255),    nullable=False),
        sa.Column("full_name",       sa.String(255),    nullable=True),
        sa.Column("profile_json",    sa.Text(),         nullable=True),
        sa.Column("skill_vector",    Vector(384),       nullable=True),
        sa.Column("market",          sa.String(10),     server_default="US", nullable=False),
        sa.Column("weakness_data",   sa.Text(),         nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("last_active",  sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active",    sa.Boolean(),               server_default="true", nullable=False),
    )

    # 3. Unique constraint + plain index on email
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_id",    "users", ["id"])

    # 4. HNSW vector index — cosine similarity for skill matching
    # m=16: 16 bi-directional links per node (memory vs recall tradeoff)
    # ef_construction=64: search width during index build (higher = better recall)
    op.execute(
        """
        CREATE INDEX ix_users_skill_vector_hnsw
        ON users
        USING hnsw (skill_vector vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
        """
    )


def downgrade() -> None:
    op.drop_index("ix_users_skill_vector_hnsw", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_id",    table_name="users")
    op.drop_table("users")
    # Note: we intentionally do NOT drop the vector extension on downgrade
    # as other tables/extensions may depend on it.
