"""
Resume Inference Agent — Phase 1 Core Agent.

WHAT IT DOES (beyond a simple parser):
  1. Parses the resume text/JSON (delegated to resume_parser.py)
  2. INFERS hidden competencies from role titles, company names, project keywords
     — without the user explicitly listing them as skills
  3. Calculates a Market Readiness Vector (MRV): a 10-dimensional float array
     that scores the user's profile against current market demands
  4. Classifies each skill into Declining | Augmented | Resilient
     (previewing Phase 4's full Disruption Audit)
  5. Returns an enriched profile with inferred_skills, mrv_score, and
     readiness_breakdown for the dashboard stat cards

WHY INFERENCE MATTERS:
  A user who lists "IT Audit Manager at Big4 for 8 years" has implicitly:
  - SOX ITGC expertise (Big4 + audit)
  - Risk assessment frameworks (COSO, COBIT)
  - Management skills (manager title)
  - Client-facing communication
  - ERP audit experience (implied by Big4 IT audit)
  These are NOT listed on the resume but ARE real skills the market values.

MRV (Market Readiness Vector) dimensions:
  [0] AI Governance literacy (0-100)
  [1] Cybersecurity depth (0-100)
  [2] Cloud maturity (0-100)
  [3] Data & Analytics (0-100)
  [4] Regulatory breadth (0-100)
  [5] Technical depth (0-100)
  [6] Leadership & Strategy (0-100)
  [7] Certification premium (0-100)
  [8] Market velocity (rate of skill acquisition, 0-100)
  [9] Resilience score (future-proofness, 0-100)

⚠️ CAPACITY FLAG: resource_tier = MEDIUM
  One LLM call per inference (if USE_LLM=True). ~500ms-2s per resume.
  For 50 concurrent uploads: runs inline in FastAPI async handler.
  At > 20 concurrent uploads/minute: route to Celery parse_resume_async task.
  LLM cost: ~0.5K tokens per resume → $0.001 per inference (Claude Haiku).
"""
import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from .base_agent import AgentResult, BaseAgent, ResourceTier

logger = logging.getLogger(__name__)

# ── Inference knowledge base ───────────────────────────────────────────────
# Maps role/company/project keywords → inferred skills
# Sorted by specificity (more specific patterns matched first)

# ── Phase 8D: Post-Doc / Academic Role Inference Map ─────────────────────
# These are implied skills for academic/research roles — the professional
# IS expected to know these even if the resume never explicitly lists them.

POST_DOC_INFERENCES: Dict[str, List[str]] = {
    "post-doc":              ["Grant Writing", "IRB Compliance", "Statistical Analysis",
                              "R", "Python", "Literature Review", "Lab Management",
                              "Research Design", "Publications", "Peer Review"],
    "postdoctoral":          ["Grant Writing", "IRB Compliance", "Statistical Analysis",
                              "R", "Python", "Literature Review", "Lab Management",
                              "Research Design", "Publications"],
    "research scientist":    ["Experimental Design", "Data Analysis", "Publications",
                              "Grant Writing", "Statistical Modeling", "R", "Python",
                              "Research Design"],
    "research associate":    ["Literature Review", "Data Collection", "Statistical Analysis",
                              "Lab Techniques", "Report Writing", "IRB Compliance"],
    "principal investigator":["NSF/NIH Grant Management", "Research Design", "Budget Management",
                               "IRB Compliance", "Lab Management", "Research Supervision"],
    "professor":             ["Curriculum Development", "Grant Writing", "Peer Review",
                              "Teaching", "Research Supervision", "Publications"],
    "lab manager":           ["Lab Safety Compliance", "SOPs", "Equipment Maintenance",
                              "Inventory Management", "IRB Compliance", "Budget Tracking"],
    "clinical researcher":   ["Clinical Trials", "GCP", "IRB Compliance", "FDA Regulations",
                              "Data Management", "HIPAA", "ICH E6 Guidelines"],
    "nsf":                   ["NSF/NIH Grant Management", "Research Design", "Compliance Reporting"],
    "nih":                   ["NIH Grant Writing", "IRB Compliance", "Clinical Protocols",
                              "FDA Regulations"],
    "irb":                   ["IRB Compliance", "Research Ethics", "Human Subjects Protection",
                              "HIPAA", "Informed Consent"],
}

# Academic/research MRV overrides — map regulatory dimension to IRB/FDA/NSF
RESEARCH_ROLES = {
    "post-doc", "postdoctoral", "research scientist", "research associate",
    "principal investigator", "professor", "lab manager", "clinical researcher",
}


ROLE_INFERENCES: Dict[str, List[str]] = {
    # Big 4 / Advisory
    "big 4": ["SOX ITGC", "Risk Assessment", "Control Testing", "Client Communication", "ERP Audit"],
    "deloitte": ["SOX ITGC", "Risk Advisory", "ERP Audit", "Data Analytics"],
    "pwc": ["SOX Auditing", "Regulatory Compliance", "Financial Controls"],
    "kpmg": ["IT Risk Management", "SOX Controls", "Audit Methodology"],
    "ey ernst": ["IT General Controls", "Process Improvement", "Risk Framework"],
    # Titles
    "chief audit executive": ["Board Reporting", "Audit Strategy", "CAE Leadership", "Risk Governance"],
    "ciso": ["Security Strategy", "Board Reporting", "Risk Governance", "Budget Management"],
    "it audit manager": ["Audit Planning", "Team Leadership", "Stakeholder Management", "Risk Reporting"],
    "audit director": ["Audit Strategy", "Team Leadership", "Executive Reporting"],
    "risk manager": ["Risk Frameworks", "ERM", "Risk Reporting", "Control Design"],
    "compliance manager": ["Regulatory Requirements", "Policy Development", "Training Programs"],
    "security architect": ["Zero Trust Architecture", "Security Design", "Threat Modeling"],
    "cloud architect": ["Multi-cloud Strategy", "Infrastructure Design", "Cost Optimisation"],
    "data scientist": ["Machine Learning", "Statistical Modeling", "Python", "Data Visualization"],
    # AI / Emerging tech
    "ai governance": ["AI Risk Management", "Model Validation", "EU AI Act", "NIST AI RMF"],
    "machine learning": ["Python", "TensorFlow/PyTorch", "Model Evaluation", "Feature Engineering"],
    # Sectors
    "financial services": ["AML/KYC Controls", "FFIEC Guidelines", "Model Risk Management"],
    "healthcare": ["HIPAA Compliance", "PHI Controls", "Healthcare IT"],
    "government": ["FISMA", "FedRAMP", "NIST SP 800-53"],
    "manufacturing": ["OT/ICS Security", "Industry 4.0", "Supply Chain Risk"],
}

# Skills mapped to market trajectory
SKILL_TRAJECTORY: Dict[str, str] = {
    # Declining (being automated)
    "manual testing": "declining",
    "spreadsheet audit": "declining",
    "paper-based controls": "declining",
    "manual sampling": "declining",
    "basic excel": "declining",
    # Augmented (AI + Human hybrid)
    "sox auditing": "augmented",
    "risk assessment": "augmented",
    "data analysis": "augmented",
    "python": "augmented",
    "sql": "augmented",
    "penetration testing": "augmented",
    "compliance management": "augmented",
    "it audit": "augmented",
    # Resilient (human-critical, hard to automate)
    "ai governance": "resilient",
    "board reporting": "resilient",
    "strategic planning": "resilient",
    "stakeholder management": "resilient",
    "team leadership": "resilient",
    "ai risk management": "resilient",
    "eu ai act": "resilient",
    "nist ai rmf": "resilient",
    "zero trust architecture": "resilient",
    "incident response": "resilient",
    "change management": "resilient",
}

# Market demand weights per MRV dimension (US market 2025-2026)
MRV_CERT_WEIGHTS: Dict[str, List[float]] = {
    # cert → adds to dimensions [ai_gov, cyber, cloud, data, reg, tech, lead, cert, velocity, resilience]
    "aigp":   [30,  5, 0, 5, 20,  5, 10, 20, 0, 15],
    "aaia":   [35,  5, 0, 5, 15,  5, 10, 15, 0, 10],
    "cisa":   [ 5, 15, 5, 5, 20, 15, 10, 25, 0,  0],
    "cissp":  [ 0, 30, 10, 5, 15, 20, 10, 25, 0,  0],
    "ccsp":   [ 0, 20, 35, 5, 10, 15,  5, 20, 0,  0],
    "cism":   [ 5, 20,  5, 5, 15, 10, 20, 20, 0,  5],
    "crisc":  [ 5, 10,  5, 5, 20, 10, 20, 20, 0,  5],
    "cgeit":  [ 5,  5,  5, 5, 15,  5, 25, 20, 0,  5],
    "aaism":  [20,  5,  5, 5, 15,  5, 10, 15, 0, 15],
    "ciasp":  [10, 25,  5, 5, 15, 20, 10, 15, 0,  5],
}

MRV_SKILL_WEIGHTS: Dict[str, List[float]] = {
    "ai governance":    [20, 0, 0, 0, 10, 5, 5, 0, 5, 15],
    "nist ai rmf":      [15, 5, 0, 0, 10, 5, 0, 0, 0, 10],
    "eu ai act":        [15, 0, 0, 0, 15, 0, 0, 0, 0, 10],
    "python":           [ 5, 5, 5, 15, 5, 15, 0, 0, 10, 5],
    "aws":              [ 0, 5, 20, 5, 5, 15, 0, 0, 5, 5],
    "azure":            [ 0, 5, 20, 5, 5, 15, 0, 0, 5, 5],
    "sox auditing":     [ 0, 5, 0, 5, 20, 10, 5, 0, 0, 0],
    "data analysis":    [ 5, 0, 5, 20, 5, 10, 0, 0, 5, 5],
    "risk assessment":  [ 5, 10, 0, 5, 15, 5, 10, 0, 0, 5],
    "zero trust":       [ 0, 20, 10, 0, 10, 15, 0, 0, 5, 10],
    "board reporting":  [ 0, 0, 0, 0, 5, 0, 20, 0, 0, 15],
    "team leadership":  [ 0, 0, 0, 0, 0, 0, 25, 0, 0, 10],
    "incident response":[ 0, 20, 5, 5, 10, 15, 5, 0, 5, 10],
    "iso 27001":        [ 0, 15, 5, 0, 15, 10, 0, 0, 0, 5],
    "machine learning": [10, 0, 5, 20, 5, 15, 0, 0, 10, 10],
}

MRV_DIMENSIONS = [
    "ai_governance", "cybersecurity", "cloud", "data_analytics",
    "regulatory", "technical", "leadership", "certification",
    "velocity", "resilience"
]

US_MARKET_DEMAND = [85, 90, 80, 75, 85, 70, 65, 80, 60, 90]  # per dimension, 2026


class ResumeInferenceAgent(BaseAgent):
    """
    Phase 1 — Resume Inference Agent.

    Input:  { "profile": dict }  (output of resume_parser)
    Output: enriched profile with:
              - inferred_skills: list of hidden competencies
              - skill_trajectory: per-skill decline/augment/resilient label
              - mrv: Market Readiness Vector (10 floats, 0-100)
              - mrv_score: weighted composite (0-100)
              - readiness_breakdown: per-dimension scores + gap vs market demand
              - market_pressure_index: Gold Standard benchmark metric (0-100)
    """

    name = "resume_inference_agent"
    resource_tier = ResourceTier.MEDIUM

    async def _execute(self, input_data: Dict[str, Any]) -> AgentResult:
        profile = input_data.get("profile", {})
        market = input_data.get("market", "US")

        result = AgentResult(success=False, agent_name=self.name)

        # Phase 8D: Detect academic/research track
        current_role = (profile.get("current_role") or "").lower()
        is_research_track = any(r in current_role for r in RESEARCH_ROLES)

        # 1. Infer hidden competencies
        inferred = _infer_competencies(profile)

        # 2. Merge explicit + inferred skills (deduplicated)
        all_skills = list(dict.fromkeys(
            [s.lower() for s in profile.get("skills", [])] + inferred
        ))

        # 3. Map to Declining / Augmented / Resilient
        trajectory = _classify_trajectory(all_skills)

        # 4. Compute Market Readiness Vector
        certs = [c.get("name", "").lower() for c in profile.get("certifications", [])]
        exp_years = profile.get("experience_years") or 0
        mrv, mrv_score = _compute_mrv(all_skills, certs, exp_years, market)

        # 5. Market Pressure Index (Gold Standard metric)
        mpi = _compute_mpi(mrv, market)

        # 6. Readiness breakdown (per-dimension score vs market demand)
        # Phase 8D: Research track uses research-specific demand baseline
        demand = (
            _research_market_demand()
            if is_research_track
            else (US_MARKET_DEMAND if market == "US" else _india_market_demand())
        )
        readiness_breakdown = [
            {
                "dimension": MRV_DIMENSIONS[i],
                "score": round(mrv[i], 1),
                "market_demand": demand[i],
                "gap": round(demand[i] - mrv[i], 1),
                "status": "strong" if mrv[i] >= demand[i] * 0.8 else
                          "developing" if mrv[i] >= demand[i] * 0.5 else "gap",
            }
            for i in range(10)
        ]

        # 7. Capacity warning if inferred skill list is very large
        if len(all_skills) > 100:
            result.flag(
                f"Profile has {len(all_skills)} skills — vector search index rebuild needed",
                migrate_to="Supabase pgvector (managed index updates)"
            )

        enriched = {
            **profile,
            "skills": [s.title() for s in all_skills[:50]],  # cap at 50 for vector
            "inferred_skills": [s.title() for s in inferred],
            "skill_trajectory": trajectory,
            "mrv": mrv,
            "mrv_score": round(mrv_score, 1),
            "market_pressure_index": mpi,
            "readiness_breakdown": readiness_breakdown,
            "career_track": "research" if is_research_track else "industry",
            "agent": self.name,
            "agent_version": self.version,
        }

        result.data = enriched
        result.success = True
        return result


# ── Inference functions ────────────────────────────────────────────────────

def _infer_competencies(profile: Dict[str, Any]) -> List[str]:
    """
    Infer hidden skills from: current_role, work_history titles/companies,
    summary text. Returns deduplicated lowercase skill list.
    """
    inferred = []
    text_to_scan = " | ".join(filter(None, [
        profile.get("current_role", ""),
        profile.get("summary", ""),
        " ".join(
            f"{j.get('title', '')} {j.get('company', '')}"
            for j in (profile.get("work_history") or [])
            if isinstance(j, dict)
        ),
    ])).lower()

    for keyword, skills in ROLE_INFERENCES.items():
        if keyword in text_to_scan:
            inferred.extend([s.lower() for s in skills])

    # Phase 8D: Post-Doc / Academic inference
    for keyword, skills in POST_DOC_INFERENCES.items():
        if keyword in text_to_scan:
            inferred.extend([s.lower() for s in skills])

    # Years of experience → leadership inference
    exp = profile.get("experience_years") or 0
    if isinstance(exp, str):
        try:
            exp = int(re.search(r"\d+", exp).group())
        except Exception:
            exp = 0
    if exp >= 8:
        inferred.extend(["stakeholder management", "strategic planning"])
    if exp >= 12:
        inferred.extend(["board reporting", "budget management"])

    return list(dict.fromkeys(inferred))


def _classify_trajectory(skills: List[str]) -> Dict[str, str]:
    """Map each skill to declining | augmented | resilient."""
    result = {}
    for skill in skills:
        sl = skill.lower()
        # Direct match
        if sl in SKILL_TRAJECTORY:
            result[skill] = SKILL_TRAJECTORY[sl]
            continue
        # Partial match
        matched = False
        for key, traj in SKILL_TRAJECTORY.items():
            if key in sl or sl in key:
                result[skill] = traj
                matched = True
                break
        if not matched:
            # Default: treat unknown skills as augmented (human+AI hybrid)
            result[skill] = "augmented"
    return result


def _compute_mrv(
    skills: List[str],
    certs: List[str],
    exp_years: int,
    market: str,
) -> Tuple[List[float], float]:
    """
    Compute the 10-dimensional Market Readiness Vector.
    Returns (vector, composite_score).
    """
    vector = [0.0] * 10

    # Contribution from skills
    for skill in skills:
        sl = skill.lower()
        for key, weights in MRV_SKILL_WEIGHTS.items():
            if key in sl or sl in key:
                for i, w in enumerate(weights):
                    vector[i] = min(100.0, vector[i] + w * 0.5)

    # Contribution from certifications
    for cert in certs:
        cl = cert.lower().replace(" ", "").replace("-", "")
        for key, weights in MRV_CERT_WEIGHTS.items():
            if key in cl:
                for i, w in enumerate(weights):
                    vector[i] = min(100.0, vector[i] + w)

    # Experience bonus (velocity + leadership)
    if exp_years >= 5:
        vector[8] = min(100.0, vector[8] + 20)  # velocity
    if exp_years >= 10:
        vector[6] = min(100.0, vector[6] + 15)  # leadership

    # Market adjustment (India market weights tech & regulatory higher)
    if market == "IN":
        vector[5] = min(100.0, vector[5] * 1.1)  # technical
        vector[4] = min(100.0, vector[4] * 1.1)  # regulatory

    # Composite score: weighted average of all 10 dimensions
    weights_composite = [0.15, 0.15, 0.10, 0.10, 0.10, 0.10, 0.10, 0.10, 0.05, 0.05]
    composite = sum(v * w for v, w in zip(vector, weights_composite))

    return vector, composite


def _compute_mpi(mrv: List[float], market: str) -> int:
    """
    Market Pressure Index — Gold Standard metric.
    Measures how much pressure the user is under to upskill NOW.

    Formula: (100 - mrv_score) × demand_urgency_factor
    High MPI (>70) means the user MUST act quickly; low MPI (<30) = ahead of curve.
    """
    demand = US_MARKET_DEMAND if market == "US" else _india_market_demand()
    gaps = [max(0, demand[i] - mrv[i]) for i in range(10)]
    avg_gap = sum(gaps) / len(gaps)
    mpi = min(100, int(avg_gap * 1.2))
    return mpi


def _india_market_demand() -> List[int]:
    """India market 2026 — higher weight on technical depth and cloud."""
    return [70, 85, 90, 80, 80, 85, 60, 75, 65, 80]


def _research_market_demand() -> List[int]:
    """
    Phase 8D — Academic/Research track market demand 2026.

    MRV dimensions remapped for research context:
      [0] AI Governance literacy → AI/ML research ethics + model governance
      [1] Cybersecurity depth   → Data security + research data compliance
      [2] Cloud maturity        → HPC/cloud compute for research
      [3] Data & Analytics      → Statistical rigor, R/Python, bioinformatics
      [4] Regulatory breadth    → IRB compliance, FDA, NSF/NIH grant rules
      [5] Technical depth       → Experimental design, lab techniques
      [6] Leadership & Strategy → Grant PI, lab management, mentorship
      [7] Certification premium → PhD, postdoc rank, discipline certs
      [8] Market velocity       → Publication rate, citation index
      [9] Resilience score      → Interdisciplinary skills, industry crossover
    """
    return [60, 50, 65, 90, 85, 80, 70, 70, 55, 75]
