"""
Phase 5 – Consolidated API Router

Mounts all Phase 2–4 endpoints onto a single FastAPI router.
Include this in user_management.py (or a new main.py) via:

    from src.backend.api_routes import router as career_router
    app.include_router(career_router, prefix="/api")

Endpoints:
  GET  /api/jobs/me             – personalised job recommendations
  POST /api/jobs/refresh        – force-refresh job cache
  GET  /api/jobs/trending       – trending roles in the market
  GET  /api/certs/recommendations – tiered cert recommendations
  GET  /api/certs/detail/{id}   – full Gold Standard cert detail
  GET  /api/certs/study/{id}    – study pack (domains, labs, questions)
  GET  /api/certs/progress      – per-domain progress tracker
  POST /api/certs/progress      – update a domain's progress score
  GET  /api/career/plan         – 5-year career roadmap
"""
import json
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator

from src.backend.user_management import UserModel, SessionLocal, get_current_user  # noqa: F401
from src.backend.engine.job_recommendation import (
    recommend_jobs_async, recommend_jobs, get_trending_roles
)
from src.backend.engine.certification_engine import (
    get_recommendations,
    get_cert_detail,
    get_study_pack,
    get_progress,
    update_domain_progress,
)
from src.backend.engine.career_plan import generate_career_plan
from src.backend.scheduler import refresh_jobs_for_user, get_cached_jobs

router = APIRouter(tags=["Career Portal"])


# ── Helpers ────────────────────────────────────────────────────────────────────

def _get_profile(user: UserModel) -> Dict[str, Any]:
    """Extract parsed profile dict from DB user, raising 400 if missing."""
    if not user.profile_json:
        raise HTTPException(
            status_code=400,
            detail="No resume on file. Upload a resume first via POST /users/me/resume",
        )
    return json.loads(user.profile_json)


def _get_progress_data(user: UserModel) -> Dict[str, Any]:
    """Read cert progress JSON stored in user profile, defaulting to empty."""
    if not user.profile_json:
        return {}
    full = json.loads(user.profile_json)
    return full.get("cert_progress", {})


def _save_progress_data(
    user: UserModel,
    progress: Dict[str, Any],
    db,
) -> None:
    full = json.loads(user.profile_json) if user.profile_json else {}
    full["cert_progress"] = progress
    user.profile_json = json.dumps(full)
    db.commit()


# ── Job endpoints ──────────────────────────────────────────────────────────────

@router.get("/jobs/me")
async def get_my_jobs(
    market: str = "US",
    remote: Optional[bool] = None,
    location: Optional[str] = None,
    salary_min: Optional[int] = None,
    current_user: UserModel = Depends(get_current_user),
):
    """
    Return ranked job recommendations for the authenticated user.
    Phase 8C: hire-probability scoring, new sources, filter params.

    Query params:
      market     "US" | "IN"
      remote     true = remote-only, false = on-site only
      location   city/state filter (e.g. "Chicago")
      salary_min minimum salary threshold
    """
    profile = _get_profile(current_user)

    # Persist market preference to user record
    db = SessionLocal()
    try:
        db_user = db.query(UserModel).filter(UserModel.id == current_user.id).first()
        if db_user:
            # Store market in profile_json
            prof_data = json.loads(db_user.profile_json) if db_user.profile_json else {}
            prof_data["preferred_market"] = market.upper()
            db_user.profile_json = json.dumps(prof_data)
            db.commit()
    finally:
        db.close()

    # Check cache first (market-aware key)
    cached = get_cached_jobs(current_user.id)
    cache_market = (cached[0].get("market","US") if cached else None)
    if cached and cache_market == market.upper():
        return {"jobs": cached, "source": "cache", "count": len(cached),
                "market": market.upper(), "market_intelligence": None}

    # Live async fetch from all sources (Phase 8C: filter params forwarded)
    result = await recommend_jobs_async(
        profile,
        market=market.upper(),
        max_results=12,
        remote=remote,
        location=location,
        salary_min=salary_min,
    )
    return {
        "jobs": result["jobs"],
        "source": "live",
        "count": len(result["jobs"]),
        "total_found": result.get("total_found", 0),
        "filtered_count": result.get("filtered_count", 0),
        "sources_used": result["sources_used"],
        "market": result["market"],
        "market_intelligence": result["market_intelligence"],
    }


@router.post("/jobs/refresh")
async def force_refresh_jobs(
    market: str = "US",
    current_user: UserModel = Depends(get_current_user),
):
    """Force-refresh job recommendations via parallel multi-API fetch."""
    profile = _get_profile(current_user)
    result  = await recommend_jobs_async(profile, market=market.upper(), max_results=12)
    refresh_jobs_for_user(current_user.id, result["jobs"])
    return {
        "message": "Jobs refreshed",
        "count": len(result["jobs"]),
        "jobs": result["jobs"],
        "market": result["market"],
        "market_intelligence": result["market_intelligence"],
    }


@router.get("/jobs/trending")
async def trending_roles(market: str = "US"):
    """Return trending IT Audit / AI Governance roles per market."""
    return {"roles": get_trending_roles(market.upper()), "market": market.upper()}


@router.get("/jobs/intelligence")
async def market_intelligence(
    market: str = "US",
    current_user: UserModel = Depends(get_current_user),
):
    """
    Run the MarketIntelligenceAgent — returns skill shift analysis,
    salary benchmarks, and top hiring companies for the selected market.
    """
    profile = _get_profile(current_user)
    try:
        from src.backend.agents.agent_registry import dispatch
        result = await dispatch(
            "market_intelligence",
            {"profile": profile, "market": market.upper()}
        )
        return result.data if result.success else {"error": result.error}
    except Exception as exc:
        # Agent unavailable — return direct market intelligence
        from src.backend.engine.job_recommendation import (
            recommend_jobs_async, _analyze_market_intelligence
        )
        r = await recommend_jobs_async(profile, market=market.upper(), max_results=10)
        return r.get("market_intelligence", {})


# ── Certification endpoints ────────────────────────────────────────────────────

@router.get("/certs/recommendations")
def cert_recommendations(current_user: UserModel = Depends(get_current_user)):
    """
    Return tiered certification recommendations (Immediate / Mid-term / Long-term)
    personalised to the user's profile, skills, and current certifications.
    Also returns domain, domain_label, and intelligence_labels for the dashboard.
    """
    from src.backend.engine.domain_classifier import (
        classify as _classify,
        domain_label as _domain_label,
        get_intelligence_labels as _get_intel_labels,
    )
    profile = _get_profile(current_user)
    recs    = get_recommendations(profile)
    domain  = _classify(profile)
    return {
        **recs,
        "domain":              domain,
        "domain_label":        _domain_label(domain),
        "intelligence_labels": _get_intel_labels(domain),
    }


@router.get("/certs/detail/{cert_id}")
def cert_detail(cert_id: str):
    """Return full Gold Standard certification detail including domains, exam info, and resources."""
    try:
        return get_cert_detail(cert_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/certs/study/{cert_id}")
def cert_study_pack(cert_id: str):
    """
    Return a focused study pack for a certification:
    domains → labs → practice questions → resources.
    """
    try:
        return get_study_pack(cert_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/certs/progress")
def get_cert_progress(
    current_user: UserModel = Depends(get_current_user),
):
    """Return per-domain study progress for all in-progress certifications."""
    profile       = _get_profile(current_user)
    progress_data = _get_progress_data(current_user)
    return get_progress(profile, progress_data)


class ProgressUpdate(BaseModel):
    cert_id:   str
    domain_id: str
    score:     int   # 0–100


@router.post("/certs/progress")
def update_cert_progress(
    update:       ProgressUpdate,
    current_user: UserModel = Depends(get_current_user),
    db=Depends(lambda: next(iter([SessionLocal()]))),
):
    """Update the completion score for a specific certification domain."""
    # Reload DB session properly
    from src.backend.user_management import get_db, SessionLocal as SL
    db = SL()
    try:
        user = db.query(UserModel).filter(UserModel.id == current_user.id).first()
        progress = _get_progress_data(user)
        updated  = update_domain_progress(
            progress, update.cert_id, update.domain_id, update.score
        )
        _save_progress_data(user, updated, db)
        return {"message": "Progress updated", "progress": updated}
    finally:
        db.close()


# ── Career plan endpoints ──────────────────────────────────────────────────────

@router.get("/career/plan")
def career_plan(current_user: UserModel = Depends(get_current_user)):
    """
    Generate and return the personalised 5-year career growth roadmap.
    Each year includes: role, salary range, certifications, skills, milestones, and actions.
    """
    profile = _get_profile(current_user)
    plan    = generate_career_plan(profile)
    return plan


# ── Artifact endpoints (Phase 3) ───────────────────────────────────────────────

class ArtifactRequest(BaseModel):
    cert_id:       str                    # "aigp" | "cisa" | "aaia" | "ciasp"
    artifact_type: str                    # "study_guide" | "cheat_sheet" | "practice_exam"
    domain_id:     Optional[str]       = None   # single domain filter (legacy)
    domain_ids:    Optional[List[str]] = None   # multi-select domains (new)

    @field_validator("cert_id", "artifact_type")
    @classmethod
    def _must_be_nonempty(cls, v: str) -> str:
        if not isinstance(v, str) or not v.strip():
            raise ValueError("must be a non-empty string")
        return v.strip().lower()


@router.get("/artifacts/catalog")
def artifacts_catalog():
    """Return available certifications and artifact types for the Study Vault."""
    from src.backend.agents.artifact_sovereign_agent import get_cert_catalog, get_artifact_types
    return {
        "certifications": list(get_cert_catalog().values()),
        "artifact_types": get_artifact_types(),
    }


@router.post("/artifacts/generate")
async def generate_artifact(
    req: ArtifactRequest,
    current_user: UserModel = Depends(get_current_user),
):
    """
    Generate a Study Vault artifact via the ArtifactSovereignAgent.

    Runs inline (no Celery required) on the v1 stack.
    For the v2 stack with Celery, this queues to the heavy worker.

    Returns the full artifact immediately (inline mode).
    For WebSocket progress, use the v2 stack /ws/artifact/{task_id} endpoint.
    """
    profile = json.loads(current_user.profile_json) if current_user.profile_json else {}
    try:
        # Call agent directly (bypasses HEAVY→Celery routing — v1 is always inline)
        from src.backend.agents.artifact_sovereign_agent import ArtifactSovereignAgent
        agent = ArtifactSovereignAgent()
        result = await agent.run({
            "cert_id":       req.cert_id,
            "artifact_type": req.artifact_type,
            "domain_id":     req.domain_id,
            "domain_ids":    req.domain_ids,
            "profile":       profile,
        })
        if result.success and result.data:
            return {
                "status":        "complete",
                "artifact":      result.data.get("artifact"),
                "cert":          result.data.get("cert"),
                "node_trace":    result.data.get("node_trace", []),
                "fidelity_score": result.data.get("fidelity_score"),
                "duration_ms":   result.duration_ms,
            }
        err_str = result.error if isinstance(result.error, str) else "Generation failed"
        return {"status": "error", "error": err_str}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/artifacts/cert/{cert_id}")
def get_cert_info(cert_id: str):
    """Return certification metadata including domains and exam structure."""
    from src.backend.agents.artifact_sovereign_agent import get_cert_catalog
    catalog = get_cert_catalog()
    cert = catalog.get(cert_id.lower())
    if not cert:
        raise HTTPException(status_code=404, detail=f"Cert '{cert_id}' not found. Valid: {list(catalog.keys())}")
    return cert


# ── Resilience endpoints (Phase 4) ─────────────────────────────────────────────

class FairCalcRequest(BaseModel):
    tef:            float   # Threat Event Frequency per year
    vulnerability:  float   # 0.0–1.0
    primary_loss:   int     # direct loss per event ($)
    secondary_loss: int = 0 # indirect loss per event ($)


@router.get("/resilience/forecast")
async def resilience_forecast(
    market: str = "US",
    current_user: UserModel = Depends(get_current_user),
):
    """
    Full 5-year resilience forecast powered by ResilienceForecasterAgent.
    Returns: resilience_score, disruption_signal, FAIR model, year-by-year forecast,
             per-skill disruption audit, and prioritised mitigation roadmap.
    """
    profile = _get_profile(current_user)
    from src.backend.agents.resilience_forecaster_agent import ResilienceForecasterAgent
    agent  = ResilienceForecasterAgent()
    result = await agent.run({"profile": profile, "market": market.upper()})
    if result.success:
        return result.data
    raise HTTPException(status_code=500, detail=result.error)


@router.post("/resilience/fair-calc")
def fair_calculator(req: FairCalcRequest):
    """
    Standalone FAIR Model calculator.
    Input: TEF, vulnerability, primary loss, secondary loss.
    Returns: SLE, ALE, risk level, and formula trace.
    No auth required — used by the interactive dashboard calculator.
    """
    from src.backend.agents.resilience_forecaster_agent import compute_fair_from_inputs
    if not (0 <= req.vulnerability <= 1):
        raise HTTPException(status_code=422, detail="vulnerability must be between 0 and 1")
    if req.tef < 0:
        raise HTTPException(status_code=422, detail="tef must be non-negative")
    return compute_fair_from_inputs(
        tef=req.tef,
        vulnerability=req.vulnerability,
        primary_loss=req.primary_loss,
        secondary_loss=req.secondary_loss,
    )


@router.get("/resilience/disruption-audit")
async def disruption_audit(
    market: str = "US",
    current_user: UserModel = Depends(get_current_user),
):
    """
    Per-skill disruption audit — returns only the skill_audit array
    for lightweight rendering in the Roadmap tab header cards.
    """
    profile = _get_profile(current_user)
    from src.backend.agents.resilience_forecaster_agent import ResilienceForecasterAgent
    agent  = ResilienceForecasterAgent()
    result = await agent.run({"profile": profile, "market": market.upper()})
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)
    d = result.data
    return {
        "resilience_score":     d["resilience_score"],
        "disruption_signal":    d["disruption_signal"],
        "skill_audit":          d["skill_audit"],
        "resilience_breakdown": d["resilience_breakdown"],
        "fair_ale":             d["fair_model"]["ale"],
        "fair_ale_label":       d["fair_model"]["ale_label"],
    }


# ── Proctor / Simulation Mode endpoints (Phase 5) ──────────────────────────

class SessionStartRequest(BaseModel):
    cert_id: str  # "aigp" | "cisa" | "aaia" | "ciasp"
    mode:    str  # "practice" | "exam"


class AnswerRequest(BaseModel):
    answer_index: int  # 0–3


@router.post("/proctor/session/start")
def proctor_session_start(
    req:          SessionStartRequest,
    current_user: UserModel = Depends(get_current_user),
):
    """
    Start a new proctored exam session.
    Returns session_id, total questions, time limit (exam mode only).
    Practice: 10 questions, immediate feedback, no timer.
    Exam:     30 questions, feedback deferred to results, 90-min timer.
    """
    from src.backend.agents.proctor_agent import create_session
    user_id = str(current_user.id) if hasattr(current_user, "id") else current_user.email
    return create_session(
        cert_id=req.cert_id.lower(),
        mode=req.mode.lower(),
        user_id=user_id,
    )


@router.get("/proctor/session/{session_id}/question")
def proctor_get_question(session_id: str, current_user: UserModel = Depends(get_current_user)):
    """
    Return the current question for the session (no correct answer or explanation).
    Includes elapsed time and (for exam mode) remaining time.
    """
    from src.backend.agents.proctor_agent import get_current_question
    result = get_current_question(session_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/proctor/session/{session_id}/answer")
def proctor_submit_answer(
    session_id:   str,
    req:          AnswerRequest,
    current_user: UserModel = Depends(get_current_user),
):
    """
    Submit an answer for the current question.
    Practice mode: returns immediate feedback (correct, explanation, distractor_logic).
    Exam mode: returns only correct/incorrect, deferring explanation to results.
    Advances the session to the next question.
    """
    from src.backend.agents.proctor_agent import submit_answer
    if not (0 <= req.answer_index <= 3):
        raise HTTPException(status_code=422, detail="answer_index must be 0–3")
    result = submit_answer(session_id, req.answer_index)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/proctor/session/{session_id}/results")
def proctor_get_results(session_id: str, current_user: UserModel = Depends(get_current_user)):
    """
    Return full results: readiness score, pass probability, domain weakness heatmap,
    and complete answer review with explanations and distractor logic.
    Available as soon as the session is completed (or can be called mid-session
    to force-end and return partial results).
    """
    from src.backend.agents.proctor_agent import get_results
    result = get_results(session_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/proctor/weakness")
def proctor_weakness_report(current_user: UserModel = Depends(get_current_user)):
    """
    Return aggregated weakness analysis across all past sessions for this user.
    Includes per-domain score, status (weak/improving/strong), and weakest domains ranked.
    """
    from src.backend.agents.proctor_agent import get_weakness_report
    user_id = str(current_user.id) if hasattr(current_user, "id") else current_user.email
    return get_weakness_report(user_id)


@router.get("/proctor/catalog")
def proctor_catalog():
    """
    Return available certifications and question counts for the Simulation Mode selector.
    No auth required — used to populate the cert picker UI.
    """
    from src.backend.agents.proctor_agent import _PROCTOR_QUESTION_BANK
    from src.backend.agents.artifact_sovereign_agent import _QUESTION_BANK as _P3_BANK, CERT_CATALOG
    catalog = []
    for cert_id, cert in CERT_CATALOG.items():
        p3_count = len(_P3_BANK.get(cert_id, []))
        p5_count = len(_PROCTOR_QUESTION_BANK.get(cert_id, []))
        catalog.append({
            "id":            cert_id,
            "name":          cert.get("name", cert_id.upper()),
            "acronym":       cert.get("acronym", cert_id.upper()),
            "total_questions": p3_count + p5_count,
            "practice_q":    10,
            "exam_q":        30,
        })
    return {"certifications": catalog}


# ── CertLab profile-driven config ─────────────────────────────────────────────

@router.get("/certlab/config")
def certlab_config(current_user: UserModel = Depends(get_current_user)):
    """
    Return profile-driven CertLab configuration:
      - Detected domain (it_audit, research_academia, data_science, …)
      - Prioritised cert list with study time + generation time estimates
      - Prebuilt flag for AAIA / CIASP (static lab available)

    Used by /certlab page to populate the cert selector dynamically
    so every user sees certifications relevant to their profile.
    """
    from src.backend.engine.domain_classifier import (
        classify as classify_domain,
        get_domain_cert_catalog,
        domain_label,
        get_intelligence_labels,
    )
    from src.backend.engine.certification_engine import get_recommendations

    profile = _get_profile(current_user)
    domain  = classify_domain(profile)

    # Get ordered cert recommendations for this profile
    recs    = get_recommendations(profile)
    ordered = (
        recs.get("immediate", []) +
        recs.get("midterm",   []) +
        recs.get("longterm",  [])
    )

    # Gen time and study time by cert type
    _GEN_SECS  = {"study_guide": "45–90s", "cheat_sheet": "20–40s", "practice_exam": "30–60s"}
    _STUDY_TIME = {"study_guide": "2–4 weeks", "cheat_sheet": "2–4 hours", "practice_exam": "1–2 hours"}

    # Static labs available for AAIA and CIASP
    _PREBUILT = {"aaia", "ciasp"}

    cert_list = []
    for cert in ordered[:8]:   # max 8 in the cert picker
        cid = cert.get("id") or cert.get("cert_id", "")
        cert_list.append({
            "id":           cid,
            "acronym":      cert.get("acronym", cid.upper()),
            "name":         cert.get("name", cid.upper()),
            "issuer":       cert.get("issuer", ""),
            "study_weeks":  cert.get("study_weeks") or cert.get("_study_weeks") or "8–12 weeks",
            "priority":     cert.get("priority", "high"),
            "rationale":    (cert.get("personalised_why") or [cert.get("rationale", "")])[0],
            "prebuilt":     cid in _PREBUILT,
            "gen_times":    _GEN_SECS,
            "study_times":  _STUDY_TIME,
            "domains":      cert.get("domains", []),
        })

    _DOMAIN_LAB_SUGGESTIONS = {
        "research_academia": [
            {"cert_id": "gcp_research", "type": "study_guide",   "label": "Research Ethics Lab"},
            {"cert_id": "nih_grant",    "type": "cheat_sheet",   "label": "NIH Grant Quick-Ref"},
            {"cert_id": "gcp_research", "type": "practice_exam", "label": "IRB Protocol Sim"},
        ],
        "it_audit": [
            {"cert_id": "aigp", "type": "study_guide",   "label": "AI Governance Lab"},
            {"cert_id": "cisa", "type": "practice_exam", "label": "CISA Audit Sim"},
            {"cert_id": "aigp", "type": "cheat_sheet",   "label": "AI Audit Quick-Ref"},
        ],
        "data_science": [
            {"cert_id": "aws_ml",         "type": "study_guide",   "label": "AWS ML Lab"},
            {"cert_id": "tensorflow_dev", "type": "practice_exam", "label": "TF Exam Sim"},
            {"cert_id": "aws_ml",         "type": "cheat_sheet",   "label": "ML Quick-Ref"},
        ],
        "engineering": [
            {"cert_id": "ckad",    "type": "study_guide",   "label": "Kubernetes Lab"},
            {"cert_id": "aws_saa", "type": "practice_exam", "label": "AWS Arch Sim"},
            {"cert_id": "ckad",    "type": "cheat_sheet",   "label": "K8s Quick-Ref"},
        ],
        "healthcare": [
            {"cert_id": "cphq", "type": "study_guide",   "label": "Quality Lab"},
            {"cert_id": "chda", "type": "practice_exam", "label": "Health Data Sim"},
            {"cert_id": "cphq", "type": "cheat_sheet",   "label": "Quality Quick-Ref"},
        ],
        "finance": [
            {"cert_id": "cfa_l1", "type": "study_guide",   "label": "CFA Level 1 Lab"},
            {"cert_id": "frm_p1", "type": "practice_exam", "label": "FRM Risk Sim"},
            {"cert_id": "cfa_l1", "type": "cheat_sheet",   "label": "Finance Quick-Ref"},
        ],
        "product": [
            {"cert_id": "pmp", "type": "study_guide",   "label": "PM Study Lab"},
            {"cert_id": "csm", "type": "practice_exam", "label": "Agile Sim"},
            {"cert_id": "pmp", "type": "cheat_sheet",   "label": "PM Quick-Ref"},
        ],
    }

    return {
        "domain":       domain,
        "domain_label": domain_label(domain),
        "certifications": cert_list,
        "type_meta": {
            "study_guide":      {"label": "Study Guide",      "gen_secs": "45–90s",  "gen_secs_max": 90,  "study_time": "2–4 weeks"},
            "cheat_sheet":      {"label": "Cheat Sheet",      "gen_secs": "20–40s",  "gen_secs_max": 40,  "study_time": "2–4 hours"},
            "practice_exam":    {"label": "Practice Exam",    "gen_secs": "30–60s",  "gen_secs_max": 60,  "study_time": "1–2 hours"},
            "practical_labwork":{"label": "Practical Labwork","gen_secs": "60–120s", "gen_secs_max": 120, "study_time": "4–8 hours"},
        },
        "suggested_labs":      _DOMAIN_LAB_SUGGESTIONS.get(domain, _DOMAIN_LAB_SUGGESTIONS["it_audit"]),
        "intelligence_labels": get_intelligence_labels(domain),
    }


# ── Universal Architect — profile-driven cert recommendations ──────────────────

@router.get("/architect/analyze")
async def architect_analyze(
    current_user: UserModel = Depends(get_current_user),
):
    """
    Analyze the authenticated user's profile and return 3 tailored cert
    recommendations with Difficulty Score + Market Value Score.

    Used by the CertLab Architect Panel on the empty state.
    """
    profile = _get_profile(current_user)
    from src.backend.agents.agent_registry import dispatch
    result = await dispatch("universal_architect", {"profile": profile})
    if result.success:
        return result.data
    raise HTTPException(status_code=500, detail=result.error or "Architect analysis failed")


# ── Profile certifications patch ──────────────────────────────────────────────

class CertPatchRequest(BaseModel):
    add:    Optional[List[str]] = []
    remove: Optional[List[str]] = []


@router.patch("/profile/certifications")
async def patch_certifications(
    req:          CertPatchRequest,
    current_user: UserModel = Depends(get_current_user),
    db=Depends(lambda: SessionLocal()),
):
    """
    Add or remove certifications from the user's profile.
    Uses _CERT_ALIASES from resume_parser to normalise cert names before storing.
    Triggers architect re-analysis on the next /api/architect/analyze call.
    """
    from src.backend.engine.resume_parser import _CERT_ALIASES
    try:
        profile = json.loads(current_user.profile_json) if current_user.profile_json else {}
        existing = [
            c["name"] if isinstance(c, dict) else c
            for c in profile.get("certifications", [])
        ]
        # Add new certs (normalised through _CERT_ALIASES)
        for cert in (req.add or []):
            normalised = _CERT_ALIASES.get(cert.strip().lower(), cert.strip().upper())
            if normalised not in existing:
                existing.append(normalised)
        # Remove certs
        for cert in (req.remove or []):
            existing = [c for c in existing if c.lower() != cert.lower()]
        profile["certifications"] = [
            {"name": c, "status": "Active", "issuer": ""}
            for c in existing
        ]
        db_user = db.query(UserModel).filter(UserModel.id == current_user.id).first()
        if db_user:
            db_user.profile_json = json.dumps(profile)
            db.commit()
        return {"certifications": existing}
    finally:
        db.close()


# ── Self-audit / health check ──────────────────────────────────────────────────

@router.get("/admin/health")
async def health_check():
    """
    Self-audit endpoint — no auth required.
    Validates: domain classification, cert recommendations, artifact fidelity.
    Returns {"all_ok": bool, "checks": [{name, passed, detail}]}
    """
    checks = []

    # 1. Domain classification
    try:
        from src.backend.engine.domain_classifier import classify
        d_dj    = classify({"current_role": "IT Audit Manager",            "skills": ["CISA", "SOX"]})
        d_pooja = classify({"current_role": "Postdoctoral Research Fellow", "skills": ["RNA-seq", "IRB"]})
        checks.append({"name": "domain_dj",    "passed": d_dj    == "it_audit",         "detail": d_dj})
        checks.append({"name": "domain_pooja", "passed": d_pooja == "research_academia", "detail": d_pooja})
    except Exception as exc:
        checks.append({"name": "domain_classification", "passed": False, "detail": str(exc)})

    # 2. Cert recommendations non-empty
    try:
        from src.backend.engine.certification_engine import get_recommendations
        recs_dj    = get_recommendations({"current_role": "IT Audit Manager",            "skills": ["CISA", "SOX"]})
        recs_pooja = get_recommendations({"current_role": "Postdoctoral Research Fellow", "skills": ["RNA-seq"]})
        checks.append({"name": "recs_dj_nonempty",    "passed": len(recs_dj.get("immediate",   [])) > 0,
                        "detail": f"{len(recs_dj.get('immediate', []))} immediate certs"})
        checks.append({"name": "recs_pooja_nonempty", "passed": len(recs_pooja.get("immediate", [])) > 0,
                        "detail": f"{len(recs_pooja.get('immediate', []))} immediate certs"})
    except Exception as exc:
        checks.append({"name": "cert_recommendations", "passed": False, "detail": str(exc)})

    # 3. Artifact fidelity (cheat_sheet — fastest generation path)
    try:
        from src.backend.agents.artifact_sovereign_agent import ArtifactSovereignAgent
        agent   = ArtifactSovereignAgent()
        result1 = await agent.run({"cert_id": "aigp",        "artifact_type": "cheat_sheet", "profile": {}})
        result2 = await agent.run({"cert_id": "gcp_research", "artifact_type": "cheat_sheet", "profile": {}})
        fidelity1 = result1.data.get("fidelity_score", 0) if (result1.success and result1.data) else 0
        fidelity2 = result2.data.get("fidelity_score", 0) if (result2.success and result2.data) else 0
        checks.append({"name": "aigp_cheat_fidelity",  "passed": fidelity1 >= 75, "detail": f"{fidelity1}/100"})
        checks.append({"name": "gcp_cheat_fidelity",   "passed": fidelity2 >= 75, "detail": f"{fidelity2}/100"})
    except Exception as exc:
        checks.append({"name": "artifact_fidelity", "passed": False, "detail": str(exc)})

    return {"all_ok": all(c["passed"] for c in checks), "checks": checks}


# ── Multi-tenant integrity audit ───────────────────────────────────────────────

_AUDIT_PROFILES = [
    {
        "label":           "IT Auditor",
        "profile":         {"current_role": "IT Audit Manager", "skills": ["CISA", "SOX", "COBIT"]},
        "expected_domain": "it_audit",
    },
    {
        "label":           "Research Scientist",
        "profile":         {"current_role": "Postdoctoral Research Fellow", "skills": ["RNA-seq", "IRB", "grant writing"]},
        "expected_domain": "research_academia",
    },
    {
        "label":           "Software Engineer",
        "profile":         {"current_role": "Senior Software Engineer", "skills": ["Python", "Docker", "Kubernetes", "Terraform"]},
        "expected_domain": "engineering",
    },
]


@router.get("/admin/tenant-audit")
async def tenant_audit():
    """
    Multi-tenant integrity audit — no auth required.
    Runs domain classification, cert recommendations, and artifact fidelity checks
    for 3 distinct profile types (Auditor, Researcher, Developer).
    Target: all domain detections correct AND artifact fidelity >= 90/100.
    """
    from src.backend.engine.domain_classifier import classify, classify_full, get_intelligence_labels
    from src.backend.engine.certification_engine import get_recommendations
    from src.backend.agents.artifact_sovereign_agent import ArtifactSovereignAgent

    agent   = ArtifactSovereignAgent()
    results = []

    for p in _AUDIT_PROFILES:
        prof   = p["profile"]
        try:
            domain  = classify(prof)
            full    = classify_full(prof)
            recs    = get_recommendations(prof)
            imm     = recs.get("immediate", [])
            cert_id = imm[0].get("cert_id", "aigp") if imm else "aigp"
            result  = await agent.run({"cert_id": cert_id, "artifact_type": "cheat_sheet", "profile": prof})
            fidelity = result.data.get("fidelity_score", 0) if (result.success and result.data) else 0
            labels   = get_intelligence_labels(domain)
            results.append({
                "profile_label":    p["label"],
                "expected_domain":  p["expected_domain"],
                "detected_domain":  domain,
                "secondary_domain": full.get("secondary"),
                "domain_correct":   domain == p["expected_domain"],
                "top_cert":         cert_id,
                "fidelity":         fidelity,
                "fidelity_passed":  fidelity >= 90,
                "sample_label":     labels.get("jd_shift", "—"),
                "cert_count":       len(imm),
                "error":            None,
            })
        except Exception as exc:
            results.append({
                "profile_label":   p["label"],
                "expected_domain": p["expected_domain"],
                "detected_domain": "error",
                "domain_correct":  False,
                "fidelity":        0,
                "fidelity_passed": False,
                "error":           str(exc),
            })

    all_passed = all(r["domain_correct"] and r["fidelity_passed"] for r in results)
    return {
        "all_passed":      all_passed,
        "target_fidelity": 90,
        "results":         results,
    }
