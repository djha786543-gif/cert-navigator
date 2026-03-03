"""
Career Portal — Application Entry Point

Mounts all routers and lifecycle hooks.

Run with:
    python -m uvicorn src.backend.main:app --reload --port 8001
"""
import json
import os

from fastapi import Request
from fastapi.responses import JSONResponse
from src.backend.user_management import app as _user_app, SessionLocal, UserModel, hash_password
from src.backend.api_routes import router as career_router
from src.backend.scheduler import start_scheduler, stop_scheduler

SEED_EMAIL    = os.getenv("SEED_EMAIL",    "dj@careernavigator.ai")
SEED_PASSWORD = os.getenv("SEED_PASSWORD", "Demo1234")
SEED_NAME     = os.getenv("SEED_NAME",     "DJ Jha")

SEED_EMAIL_2    = os.getenv("SEED_EMAIL_2",    "pooja@careernavigator.ai")
SEED_PASSWORD_2 = os.getenv("SEED_PASSWORD_2", "Demo1234")
SEED_NAME_2     = os.getenv("SEED_NAME_2",     "Pooja Jha")

# Pre-baked profiles so domain classifier works immediately after Railway restart
# without requiring a resume upload.
_DJ_PROFILE = {
    "current_role": "IT Audit Manager",
    "target_role":  "AI Governance Director",
    "experience_years": 12,
    "skills": [
        "CISA", "SOX", "ITGC", "COBIT 2019", "NIST CSF", "risk management",
        "IT controls", "compliance", "internal audit", "IS audit",
        "data governance", "AI governance", "COSO", "third-party risk",
    ],
    "certifications": [{"name": "CISA"}],
    "summary": (
        "IT Audit Manager with 12 years of experience in SOX compliance, "
        "IT general controls, and risk-based audit programmes."
    ),
    "education": [{"degree": "MBA", "field": "Information Systems"}],
}

_POOJA_PROFILE = {
    "current_role": "Postdoctoral Research Fellow",
    "target_role":  "Principal Research Scientist",
    "experience_years": 7,
    "skills": [
        "RNA-seq", "CRISPR", "IRB protocols", "grant writing", "bioinformatics",
        "research design", "publications", "peer review", "laboratory management",
        "genomics", "cell biology", "statistical analysis", "NIH grant writing",
    ],
    "certifications": [],
    "summary": (
        "Postdoctoral researcher specialising in molecular biology and genomics "
        "with extensive IRB protocol and NIH grant-writing experience."
    ),
    "education": [{"degree": "PhD", "field": "Molecular Biology"}],
}

# ── Global error handlers — returns clean strings, never raw Pydantic dicts ──

def _flatten_detail(exc) -> str:
    """Convert any exception to a user-safe string."""
    # Pydantic v2 ValidationError — list of {type, loc, msg, input}
    if hasattr(exc, "errors"):
        try:
            return "; ".join(e.get("msg", str(e)) for e in exc.errors())
        except Exception:
            pass
    # FastAPI HTTPException — already has .detail
    if hasattr(exc, "detail"):
        d = exc.detail
        if isinstance(d, list):
            return "; ".join(
                e.get("msg", str(e)) if isinstance(e, dict) else str(e) for e in d
            )
        return str(d)
    return str(exc)


@_user_app.exception_handler(Exception)
async def _generic_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": _flatten_detail(exc)},
    )


# Pydantic v1/v2 RequestValidationError (422 from FastAPI body validation)
try:
    from fastapi.exceptions import RequestValidationError

    @_user_app.exception_handler(RequestValidationError)
    async def _validation_error_handler(request: Request, exc: RequestValidationError):
        msgs = [e.get("msg", str(e)) if isinstance(e, dict) else str(e) for e in exc.errors()]
        return JSONResponse(
            status_code=422,
            content={"detail": "; ".join(msgs)},
        )
except ImportError:
    pass


# Attach the career router to the existing user_management app
_user_app.include_router(career_router, prefix="/api")


def _seed_user(email: str, password: str, name: str, profile: dict, db) -> None:
    """Create or update a demo user. Always refreshes profile_json so domain
    classifier returns correct results even after Railway wipes SQLite."""
    user = db.query(UserModel).filter_by(email=email).first()
    if not user:
        user = UserModel(
            email=email,
            hashed_password=hash_password(password),
            full_name=name,
        )
        db.add(user)
    # Always write the profile so it survives Railway DB resets
    if not user.profile_json:
        user.profile_json = json.dumps(profile)
    db.commit()


def _seed_demo_user():
    """Seed both demo users on every startup (SQLite is ephemeral on Railway)."""
    db = SessionLocal()
    try:
        _seed_user(SEED_EMAIL,   SEED_PASSWORD,   SEED_NAME,   _DJ_PROFILE,    db)
        _seed_user(SEED_EMAIL_2, SEED_PASSWORD_2, SEED_NAME_2, _POOJA_PROFILE, db)
    finally:
        db.close()


@_user_app.on_event("startup")
def on_startup():
    _seed_demo_user()
    start_scheduler()


@_user_app.on_event("shutdown")
def on_shutdown():
    stop_scheduler()


# Expose as `app` so uvicorn can pick it up
app = _user_app
