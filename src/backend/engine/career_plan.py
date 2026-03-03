"""
Phase 4 – 5-Year Career Growth Plan Engine

Generates a personalised, role-specific 5-year roadmap using:
  - Current role, target role, experience, and skills from the user's profile
  - Certification recommendations from Phase 3
  - Market salary data for Torrance / LA / Remote roles

Output structure (one entry per year):
  {
    "year": 1,
    "year_label": "2026",
    "phase": "Establish",
    "target_role": "...",
    "salary_range": {"min": ..., "max": ...},
    "key_milestones": [...],
    "certifications_to_earn": [...],
    "skills_to_develop": [...],
    "action_items": [...],
    "success_metrics": [...],
  }
"""
from datetime import datetime
from typing import Any, Dict, List


# ── Salary benchmarks (2026 Torrance / LA / Remote market) ───────────────────
_SALARY_BANDS: Dict[str, Dict[str, int]] = {
    "IT Auditor":                         {"min": 85_000,  "max": 105_000},
    "Senior IT Auditor":                  {"min": 105_000, "max": 125_000},
    "IT Audit Manager":                   {"min": 120_000, "max": 150_000},
    "Senior IT Audit Manager":            {"min": 140_000, "max": 170_000},
    "AI Audit Manager":                   {"min": 145_000, "max": 175_000},
    "Director of IT Audit":               {"min": 165_000, "max": 200_000},
    "AI Governance Lead":                 {"min": 135_000, "max": 165_000},
    "IT Risk Director":                   {"min": 170_000, "max": 210_000},
    "Chief Audit Executive":              {"min": 185_000, "max": 230_000},
    "Chief Audit Executive / AI Audit Director": {"min": 185_000, "max": 240_000},
    "VP of Internal Audit":               {"min": 175_000, "max": 220_000},
    "Cloud Security Auditor":             {"min": 125_000, "max": 155_000},
    "IT Risk Manager":                    {"min": 115_000, "max": 145_000},
}

_DEFAULT_BAND = {"min": 100_000, "max": 130_000}


# ── Role progression templates ─────────────────────────────────────────────────
_ROLE_PROGRESSIONS: Dict[str, List[str]] = {
    "it audit manager": [
        "IT Audit Manager",
        "Senior IT Audit Manager / AI Audit Manager",
        "Director of IT Audit",
        "VP of Internal Audit / IT Risk Director",
        "Chief Audit Executive / AI Audit Director",
    ],
    "senior it auditor": [
        "Senior IT Auditor",
        "IT Audit Manager",
        "AI Audit Manager",
        "Director of IT Audit",
        "Chief Audit Executive",
    ],
    "it auditor": [
        "IT Auditor",
        "Senior IT Auditor",
        "IT Audit Manager",
        "Senior IT Audit Manager",
        "Director of IT Audit",
    ],
    "default": [
        "IT Audit Professional (Year 1)",
        "Senior Contributor",
        "Manager / Lead",
        "Director",
        "Executive / CAE",
    ],
}


def _get_progression(current_role: str) -> List[str]:
    key = (current_role or "").lower()
    for pattern, roles in _ROLE_PROGRESSIONS.items():
        if pattern in key:
            return roles
    return _ROLE_PROGRESSIONS["default"]


# ── Certification roadmap per year ─────────────────────────────────────────────
_CERT_ROADMAP = [
    ["AAISM", "AIGP"],           # Year 1 — establish AI governance credibility
    ["CCSP"],                    # Year 2 — cloud security (CCSP)
    ["CISM"],                    # Year 3 — security management leadership
    ["CRISC"],                   # Year 4 — enterprise risk authority
    ["CGEIT"],                   # Year 5 — board-level governance
]

# ── Skill development roadmap per year ────────────────────────────────────────
_SKILL_ROADMAP = [
    ["AI audit methodology", "EU AI Act compliance", "NIST AI RMF", "Python for audit automation", "AI model risk assessment"],
    ["Cloud security controls (CCSP domains)", "CSPM tooling (Prisma Cloud / Wiz)", "Zero Trust architecture", "MLOps monitoring"],
    ["Information security management", "Security programme design", "Incident response leadership", "Board risk reporting"],
    ["Enterprise risk quantification (FAIR)", "CRISC risk scenarios", "KRI design", "Continuous control monitoring"],
    ["IT governance frameworks (COBIT 2019)", "Board reporting and communication", "AI governance board committee", "Strategy and value delivery"],
]

# ── Milestone templates per year ───────────────────────────────────────────────
_MILESTONES = [
    [
        "Earn AAISM credential (Q2 2026)",
        "Earn AIGP credential (Q3 2026)",
        "Lead first AI governance audit engagement",
        "Publish internal AI audit methodology",
        "Join ISACA AI Working Group or IAPP local chapter",
    ],
    [
        "Pass CCSP exam (Q4 2026 / Q1 2027)",
        "Lead cloud security audit for a major platform (AWS/Azure)",
        "Develop cloud audit framework for the organisation",
        "Present cloud risk findings to the audit committee",
        "Mentor 1 junior auditor in AI/cloud concepts",
    ],
    [
        "Earn CISM credential (Q1–Q2 2027)",
        "Own security programme assessment for an enterprise client",
        "Design and deliver security awareness campaign",
        "Lead tabletop incident response exercise",
        "Expand professional network: 2 speaking engagements or publications",
    ],
    [
        "Earn CRISC credential (Q2–Q3 2027)",
        "Own enterprise IT risk register for the organisation",
        "Implement continuous control monitoring programme",
        "Build AI risk quantification model using FAIR",
        "Target: Director of IT Audit / IT Risk Director title",
    ],
    [
        "Earn CGEIT credential (2028)",
        "Achieve Chief Audit Executive or AI Audit Director role",
        "Present AI governance strategy to Board of Directors",
        "Establish AI Audit Centre of Excellence",
        "Publish thought leadership article / speak at ISACA or IAPP conference",
    ],
]

# ── Action items per year ──────────────────────────────────────────────────────
_ACTIONS = [
    [
        "Register for AAISM exam — target completion by Q2 2026",
        "Enrol in IAPP AIGP study programme (officialcourse + QAE database)",
        "Set up daily AI news tracker (IAPP Daily Dashboard, MIT Technology Review)",
        "Request AI audit assignment from current team or propose a pilot",
        "Begin LinkedIn thought leadership: post AI audit insights monthly",
    ],
    [
        "Register for CCSP exam after AIGP completion",
        "Complete AWS Cloud Practitioner or Azure Fundamentals (free)",
        "Shadow or co-lead a cloud security audit engagement",
        "Build CCSP study group within the organisation",
        "Update resume and LinkedIn to reflect AAISM + AIGP credentials",
    ],
    [
        "Register for CISM exam after CCSP completion",
        "Volunteer for incident response team or tabletop exercise facilitation",
        "Develop security programme roadmap for current employer",
        "Target a Senior Manager or equivalent title conversation with leadership",
        "Build ISACA chapter relationships for visibility and career opportunities",
    ],
    [
        "Register for CRISC exam",
        "Propose and implement a risk quantification pilot using FAIR model",
        "Apply for Director-level positions internally and externally",
        "Build board-ready risk reporting capability",
        "Develop AI risk framework integrating CRISC and NIST AI RMF",
    ],
    [
        "Register for CGEIT exam",
        "Target CAE / AI Audit Director role applications",
        "Engage with Board-level discussions on AI governance",
        "Establish AI Audit CoE with documented methodology",
        "Consider adjunct teaching, consulting, or advisory board work",
    ],
]


# ── Public API ─────────────────────────────────────────────────────────────────

def generate_career_plan(profile: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate a personalised 5-year career roadmap.

    Args:
        profile: Normalised user profile from resume_parser.

    Returns:
        {
          "user_name": str,
          "current_role": str,
          "target_role": str,
          "base_year": int,
          "years": [{ year data }, ...],
          "five_year_summary": { ... },
        }
    """
    current_role = profile.get("current_role") or "IT Audit Professional"
    target_role  = profile.get("target_role")  or "Chief Audit Executive"
    held_certs   = [
        (c.get("name", c) if isinstance(c, dict) else str(c))
        for c in profile.get("certifications", [])
    ]

    progression = _get_progression(current_role)
    base_year   = datetime.utcnow().year
    years       = []

    for i in range(5):
        role_this_year = progression[i] if i < len(progression) else progression[-1]
        band = _SALARY_BAND_FOR(role_this_year)

        # Filter out already-held certs
        certs_for_year = [c for c in _CERT_ROADMAP[i] if c not in held_certs]

        years.append({
            "year":                  i + 1,
            "year_label":            str(base_year + i),
            "phase":                 _PHASE_LABEL[i],
            "target_role":           role_this_year,
            "salary_range":          band,
            "key_milestones":        _MILESTONES[i],
            "certifications_to_earn": certs_for_year,
            "skills_to_develop":     _SKILL_ROADMAP[i],
            "action_items":          _ACTIONS[i],
            "success_metrics":       _SUCCESS_METRICS[i],
        })

    five_year = _five_year_summary(progression, base_year, profile)

    return {
        "user_name":          profile.get("name", "Professional"),
        "current_role":       current_role,
        "target_role":        target_role,
        "current_certs":      held_certs,
        "base_year":          base_year,
        "years":              years,
        "five_year_summary":  five_year,
    }


# ── Helpers ────────────────────────────────────────────────────────────────────

_PHASE_LABEL = ["Establish", "Expand", "Lead", "Direct", "Transform"]

_SUCCESS_METRICS = [
    ["AAISM + AIGP earned", "1 AI audit completed", "LinkedIn profile updated with AI credentials"],
    ["CCSP earned", "Cloud audit methodology documented", "Senior Manager title conversation initiated"],
    ["CISM earned", "Security programme ownership", "IR exercise facilitated", "External speaking/publication"],
    ["CRISC earned", "Director title secured", "FAIR risk model deployed", "Board risk reporting delivered"],
    ["CGEIT earned", "CAE / Director role secured", "AI CoE established", "Board-level AI strategy presented"],
]


def _SALARY_BAND_FOR(role: str) -> Dict[str, int]:
    role_clean = role.lower()
    # Sort by key length descending so more-specific keys win over generic ones
    for key, band in sorted(_SALARY_BANDS.items(), key=lambda x: len(x[0]), reverse=True):
        if key.lower() in role_clean:
            return band
    return _DEFAULT_BAND


def _five_year_summary(
    progression: List[str],
    base_year: int,
    profile: Dict[str, Any],
) -> Dict[str, Any]:
    start_band = _SALARY_BAND_FOR(profile.get("current_role") or "IT Audit Manager")
    end_band   = _SALARY_BAND_FOR(progression[-1])
    return {
        "start_role":             profile.get("current_role", ""),
        "end_role":               progression[-1],
        "total_certs_to_earn":    5,  # AAISM, AIGP, CCSP, CISM, CRISC, CGEIT (minus held)
        "salary_uplift_estimate": {
            "start_min": start_band["min"],
            "start_max": start_band["max"],
            "end_min":   end_band["min"],
            "end_max":   end_band["max"],
            "pct_increase": round(
                ((end_band["min"] - start_band["min"]) / start_band["min"]) * 100, 1
            ) if start_band["min"] > 0 else 0,
        },
        "years_covered":          f"{base_year}–{base_year + 4}",
        "key_theme":              "AI Governance Leadership — the rare auditor who bridges IT, AI, and board strategy",
        "critical_actions":       [
            "Earn AIGP within 12 months — this is the career-defining differentiator for 2026",
            "Volunteer for AI audit projects before you feel 100% ready",
            "Build public profile: LinkedIn posts, ISACA chapter visibility",
            "Never stop learning — set 2 hours/week of structured study as non-negotiable",
        ],
    }
