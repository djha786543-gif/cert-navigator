"""
Pydantic v2 schemas for request/response validation.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, EmailStr, field_validator


# ── Auth ──────────────────────────────────────────────────────────────────
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    market: str = "US"

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v

    @field_validator("market")
    @classmethod
    def market_valid(cls, v: str) -> str:
        if v not in ("US", "IN"):
            raise ValueError("market must be 'US' or 'IN'")
        return v


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    email: Optional[str] = None


# ── User ──────────────────────────────────────────────────────────────────
class UserResponse(BaseModel):
    id: int
    email: str
    full_name: Optional[str]
    market: str
    created_at: datetime

    model_config = {"from_attributes": True}


class UserProfile(BaseModel):
    id: int
    email: str
    full_name: Optional[str]
    market: str
    profile: Optional[Dict[str, Any]]
    weakness_summary: Optional[Dict[str, Any]] = None
    skill_count: int = 0

    model_config = {"from_attributes": True}


class MarketToggle(BaseModel):
    market: str

    @field_validator("market")
    @classmethod
    def market_valid(cls, v: str) -> str:
        if v not in ("US", "IN"):
            raise ValueError("market must be 'US' or 'IN'")
        return v


# ── Weakness Tracking (Gold Standard port) ────────────────────────────────
class DomainRecord(BaseModel):
    correct: int = 0
    total: int = 0
    streak: int = 0


class TopicRecord(BaseModel):
    correct: int = 0
    total: int = 0
    recent: List[Dict[str, Any]] = []


class WeaknessPayload(BaseModel):
    """
    Schema for the /users/me/weakness endpoint.
    Mirrors the WeaknessTracker data structure from certlab-saas-v2.html.
    """
    domains: Dict[str, DomainRecord] = {}
    topics: Dict[str, TopicRecord] = {}
    history: List[Dict[str, Any]] = []


class WeaknessSummary(BaseModel):
    predicted_exam_score: Optional[int]
    weak_domains: List[Dict[str, Any]]
    recommendations: List[Dict[str, Any]]
    total_questions_answered: int
