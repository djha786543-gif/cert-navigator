"""Skills Gap Analyzer v2 API endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models.user import User
from ..schemas.skills_gap import SkillsGapAnalysisResponse, SkillsGapRequest
from ..services.auth_service import get_current_user
from ..services.skills_gap_service import SkillsGapService

router = APIRouter(prefix="/api/skills-gap", tags=["Skills Gap"])


@router.post("/analyze", response_model=SkillsGapAnalysisResponse)
async def analyze_skills_gap(
    payload: SkillsGapRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SkillsGapAnalysisResponse:
    service = SkillsGapService()
    return await service.analyze(
        db=db,
        user_id=current_user.id,
        role_key=payload.role_key,
        market=payload.market or current_user.market,
    )
