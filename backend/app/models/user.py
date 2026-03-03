"""
User ORM model.

Key design decisions:
- skill_vector: Vector(384) using pgvector — stores all-MiniLM-L6-v2 embeddings.
  An HNSW index enables sub-millisecond cosine similarity search across all users.
- weakness_data: JSON blob (serialised WeaknessTracker state from the Gold Standard).
- market: 'US' | 'IN' toggle persisted per user.

⚠️ CAPACITY FLAG: The HNSW index (m=16, ef_construction=64) consumes ~1.5x
   the raw vector storage. For 50K users × 384 dims × 4 bytes = ~29 MB raw,
   ~44 MB with index. Well within local machine limits. At 1M users → 880 MB,
   which is when you'd move to Supabase pgvector or AWS RDS with pgvector.
"""
from datetime import datetime
from typing import Optional

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(
        sa.String(255), unique=True, index=True, nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(sa.String(255))

    # ── Profile ────────────────────────────────────────────────────────────
    profile_json: Mapped[Optional[str]] = mapped_column(sa.Text)
    # 384-dimensional skill embedding — populated on resume upload
    skill_vector: Mapped[Optional[list]] = mapped_column(Vector(384), nullable=True)

    # ── Market toggle (US / India) ─────────────────────────────────────────
    market: Mapped[str] = mapped_column(sa.String(10), server_default="US")

    # ── Weakness Tracking Engine state (Gold Standard port) ───────────────
    # Stores: { domains: {}, topics: {}, history: [] }
    weakness_data: Mapped[Optional[str]] = mapped_column(sa.Text)

    # ── Metadata ───────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now()
    )
    last_active: Mapped[Optional[datetime]] = mapped_column(
        sa.DateTime(timezone=True), onupdate=sa.func.now()
    )
    is_active: Mapped[bool] = mapped_column(sa.Boolean, server_default="true")

    # ── pgvector HNSW index ────────────────────────────────────────────────
    # HNSW is preferred over IVFFlat for < 1M rows: no training needed,
    # better recall (0.99+), and insert performance is acceptable.
    __table_args__ = (
        sa.Index(
            "ix_users_skill_vector_hnsw",
            skill_vector,
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"skill_vector": "vector_cosine_ops"},
        ),
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email}>"
