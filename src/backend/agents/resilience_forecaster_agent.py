"""
Resilience Forecaster Agent — Phase 4 Core Agent (MEDIUM tier).

WHAT IT DOES:
  1. Disruption Audit   — classifies every skill as Declining/Augmented/Resilient
                          with a quantified automation risk score (0-100)
  2. FAIR Model Calc    — applies Factor Analysis of Information Risk to career
                          disruption: TEF × Vulnerability × Annual Earnings = ALE
  3. Resilience Score   — composite 0-100 index derived from MRV + skill mix
  4. 5-Year Forecast    — year-by-year projection of skills under threat,
                          MPI evolution, and milestone criticality
  5. Mitigation Roadmap — prioritised action plan to shift from Declining → Resilient

FAIR MODEL ADAPTATION FOR CAREER RISK:
  Threat:       AI/Automation capability growth (doubles every ~2 years)
  Asset:        User's annual earnings (career capital)
  TEF:          How frequently AI can substitute user's task domain per year
  Vulnerability: 1 − (resilience ratio of user's skill portfolio)
  Loss Magnitude: Earnings at risk (salary × automation-exposed fraction)
  ALE:          Annualised risk in dollar terms (probabilistic)

OUTPUT SCHEMA:
  {
    "resilience_score":       int (0-100),
    "disruption_signal":      "Critical" | "High" | "Moderate" | "Low",
    "fair_model":             { TEF, vulnerability, ale, annual_earnings_at_risk },
    "skill_audit":            [ { skill, trajectory, automation_risk, action } ],
    "year_forecast":          [ { year, mpi, resilience_score, primary_risk, action } ],
    "mitigation_plan":        [ { priority, action, impact, timeline } ],
    "resilience_breakdown":   { declining_pct, augmented_pct, resilient_pct },
  }

⚠️ CAPACITY FLAG: resource_tier = MEDIUM
  Pure Python computation — no LLM calls, no I/O. <50ms per execution.
  Safe for 50 concurrent users inline.
  Optional LLM upgrade in Phase 6: richer natural-language mitigation narrative.
"""
import logging
import math
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from .base_agent import AgentResult, BaseAgent, ResourceTier
from .resume_inference_agent import (
    SKILL_TRAJECTORY,
    MRV_DIMENSIONS,
    US_MARKET_DEMAND,
    _compute_mrv,
    _infer_competencies,
    _classify_trajectory,
)

logger = logging.getLogger(__name__)


# ── Automation Risk Database ───────────────────────────────────────────────
# Per-skill automation risk score (0-100): how likely AI replaces this skill
# by 2030 given current trajectory. Based on McKinsey, Oxford, WEF research.

_AUTOMATION_RISK: Dict[str, int] = {
    # Declining (high automation risk)
    "manual testing":             95,
    "spreadsheet audit":          90,
    "paper-based controls":       88,
    "manual sampling":            85,
    "basic excel":                80,
    "data entry":                 95,
    "manual reconciliation":      88,
    "transaction monitoring":     75,
    "rule-based fraud detection": 80,
    "manual report generation":   85,
    "basic compliance checklist": 78,
    # Augmented (medium automation risk — human still needed)
    "sox auditing":               45,
    "risk assessment":            40,
    "data analysis":              35,
    "python":                     30,
    "sql":                        35,
    "penetration testing":        30,
    "compliance management":      42,
    "it audit":                   40,
    "financial auditing":         50,
    "vendor management":          45,
    "project management":         40,
    "process documentation":      60,
    "gap analysis":               50,
    "control testing":            55,
    # Resilient (low automation risk — human-critical)
    "ai governance":               8,
    "board reporting":             5,
    "strategic planning":         10,
    "stakeholder management":      8,
    "team leadership":             5,
    "ai risk management":          8,
    "eu ai act":                  10,
    "nist ai rmf":                12,
    "zero trust architecture":    15,
    "incident response":          18,
    "change management":          12,
    "ethics and compliance":      10,
    "crisis management":           8,
    "executive communication":     5,
    "talent development":         10,
    "client advisory":            12,
    "regulatory interpretation":  15,
    "innovation leadership":      10,
}

_DEFAULT_AUTOMATION_RISK: Dict[str, int] = {
    "declining":  80,
    "augmented":  42,
    "resilient":  12,
}

# ── Mitigation Actions ──────────────────────────────────────────────────────
# Prioritised actions per trajectory type

_MITIGATION_ACTIONS: Dict[str, Dict[str, Any]] = {
    "declining": {
        "immediate": "Upskill from this task — AI will automate it within 2-3 years",
        "cert":      "AIGP or AAIA certification converts audit skills to AI-audit leadership",
        "timeline":  "6-12 months",
        "impact":    "high",
    },
    "augmented": {
        "immediate": "Layer AI tooling on top — become the human who directs AI doing this task",
        "cert":      "CISA + Python skills amplify your value in this domain",
        "timeline":  "12-24 months",
        "impact":    "medium",
    },
    "resilient": {
        "immediate": "Double down — this skill is defensible through 2030+",
        "cert":      "Deepen with governance certs (AIGP, CISM) to stay at the frontier",
        "timeline":  "Ongoing",
        "impact":    "low",
    },
}

# ── Market velocity projection ──────────────────────────────────────────────
# How fast automation advances per year (compound doubling of AI capability)

_AUTOMATION_VELOCITY_PER_YEAR = 1.18   # 18% capability increase per year (conservative)

# MPI penalty per year for inaction (assuming no upskilling)
_MPI_DRIFT_PER_YEAR = 4.5   # MPI increases ~4.5 points/year without upskilling

# Certification MPI reduction (earning a cert reduces MPI)
_CERT_MPI_REDUCTION: Dict[str, int] = {
    "aigp":  22,
    "aaia":  18,
    "cisa":  14,
    "cissp": 12,
    "ccsp":  12,
    "cism":  10,
    "crisc":  8,
}


# ── Agent ──────────────────────────────────────────────────────────────────

class ResilienceForecasterAgent(BaseAgent):
    """
    Phase 4 — Resilience Forecaster Agent.

    Input:  { "profile": dict, "market": "US"|"IN", "target_salary": optional int }
    Output: full resilience forecast with FAIR model and mitigation roadmap
    """

    name = "resilience_forecaster_agent"
    resource_tier = ResourceTier.MEDIUM

    async def _execute(self, input_data: Dict[str, Any]) -> AgentResult:
        profile       = input_data.get("profile", {})
        market        = input_data.get("market", "US").upper()
        target_salary = input_data.get("target_salary")

        result = AgentResult(success=False, agent_name=self.name)

        # 1. Skill inventory (explicit + inferred)
        inferred  = _infer_competencies(profile)
        all_skills = list(dict.fromkeys(
            [s.lower() for s in profile.get("skills", [])] + inferred
        ))
        trajectory = _classify_trajectory(all_skills)

        # 2. MRV and composite scores
        certs     = [
            (c.get("name", "") if isinstance(c, dict) else str(c)).lower()
            for c in profile.get("certifications", [])
        ]
        exp_years = profile.get("experience_years") or 0
        mrv, mrv_score = _compute_mrv(all_skills, certs, exp_years, market)

        # 3. Disruption Audit (per-skill)
        skill_audit = _build_skill_audit(all_skills, trajectory)

        # 4. Resilience Score
        resilience_score, breakdown = _compute_resilience_score(skill_audit, mrv_score, certs)

        # 5. FAIR Model — career disruption risk
        current_salary = _estimate_salary(profile, market)
        if target_salary:
            current_salary = target_salary
        fair = _compute_fair_model(skill_audit, resilience_score, current_salary, market)

        # 6. Disruption signal
        disruption_signal = _classify_disruption(fair["ale"], current_salary, resilience_score)

        # 7. 5-year forecast
        base_mpi = profile.get("market_pressure_index", 60)
        year_forecast = _build_year_forecast(
            base_mpi, resilience_score, certs, skill_audit, market, exp_years
        )

        # 8. Mitigation roadmap
        mitigation = _build_mitigation_plan(skill_audit, certs, resilience_score, market)

        # 9. Capacity flag if disruption is critical
        if disruption_signal == "Critical":
            result.flag(
                f"Career disruption ALE = ${fair['ale']:,.0f}/year. "
                "Immediate action required — 60%+ of skills are Declining.",
                migrate_to="Phase 5 ProctorAgent for intensive upskill simulation"
            )

        result.data = {
            "resilience_score":     resilience_score,
            "disruption_signal":    disruption_signal,
            "fair_model":           fair,
            "skill_audit":          skill_audit,
            "resilience_breakdown": breakdown,
            "year_forecast":        year_forecast,
            "mitigation_plan":      mitigation,
            "mrv_score":            mrv_score,
            "mrv":                  mrv,
            "current_salary_est":   current_salary,
            "market":               market,
            "snapshot_date":        datetime.utcnow().strftime("%Y-%m-%d"),
            "certs_held":           certs,
            "experience_years":     exp_years,
        }
        result.success = True
        return result


# ── Pure computation helpers ────────────────────────────────────────────────

def _build_skill_audit(
    skills: List[str],
    trajectory: Dict[str, str],
) -> List[Dict[str, Any]]:
    """Per-skill disruption audit with automation risk score and action."""
    audit = []
    for skill in skills[:30]:  # cap at 30 to keep response manageable
        traj = trajectory.get(skill, "augmented")
        risk = _AUTOMATION_RISK.get(skill, _DEFAULT_AUTOMATION_RISK[traj])
        action_data = _MITIGATION_ACTIONS[traj]
        audit.append({
            "skill":            skill.title(),
            "trajectory":       traj,
            "automation_risk":  risk,
            "timeline_to_risk": _risk_timeline(risk),
            "action":           action_data["immediate"],
            "recommended_cert": action_data["cert"],
            "mitigation_impact":action_data["impact"],
        })
    # Sort: declining first, then augmented, then resilient; within each by risk desc
    order = {"declining": 0, "augmented": 1, "resilient": 2}
    return sorted(audit, key=lambda x: (order.get(x["trajectory"], 1), -x["automation_risk"]))


def _risk_timeline(risk: int) -> str:
    if risk >= 80:  return "1-2 years"
    if risk >= 60:  return "2-3 years"
    if risk >= 40:  return "3-5 years"
    if risk >= 20:  return "5-8 years"
    return "10+ years"


def _compute_resilience_score(
    skill_audit: List[Dict],
    mrv_score: float,
    certs: List[str],
) -> Tuple[int, Dict[str, Any]]:
    """
    Resilience Score (0-100):
      40% weight → skill portfolio mix (declining/augmented/resilient ratio)
      40% weight → MRV composite score
      20% weight → certification premium
    """
    if not skill_audit:
        skill_score = 50
        declining_pct = augmented_pct = resilient_pct = 33
    else:
        counts = {"declining": 0, "augmented": 0, "resilient": 0}
        for s in skill_audit:
            counts[s["trajectory"]] = counts.get(s["trajectory"], 0) + 1
        total = sum(counts.values()) or 1
        declining_pct = round(counts["declining"] / total * 100)
        augmented_pct  = round(counts["augmented"] / total * 100)
        resilient_pct  = round(counts["resilient"] / total * 100)
        # Skill score: penalise declining, reward resilient
        skill_score = max(0, min(100,
            resilient_pct * 1.0 + augmented_pct * 0.5 - declining_pct * 0.3
        ))

    # Cert premium (each cert adds up to 5 points)
    cert_premium = min(20, sum(
        8 if c in ("aigp", "aaia", "cissp") else
        6 if c in ("cisa", "ccsp", "cism") else 4
        for c in certs
    ))

    score = int(skill_score * 0.40 + mrv_score * 0.40 + cert_premium * 0.20)
    score = max(5, min(98, score))

    return score, {
        "declining_pct":  declining_pct,
        "augmented_pct":  augmented_pct,
        "resilient_pct":  resilient_pct,
        "skill_score":    round(skill_score),
        "mrv_score":      round(mrv_score),
        "cert_premium":   cert_premium,
        "score_formula":  "40% skill mix + 40% MRV + 20% cert premium",
    }


def _estimate_salary(profile: Dict[str, Any], market: str) -> int:
    """Estimate current salary from role and experience for FAIR model base."""
    role = (profile.get("current_role") or "").lower()
    exp  = profile.get("experience_years") or 0

    if market == "US":
        if "chief audit" in role or "cae" in role:                    base = 195_000
        elif "vp" in role or "director" in role:                      base = 185_000
        elif "ai governance" in role or "ai audit" in role:           base = 155_000
        elif "manager" in role or "lead" in role:                     base = 140_000
        elif "senior" in role:                                         base = 110_000
        else:                                                          base =  90_000
        return base + min(exp * 2_500, 25_000)
    else:  # India (INR)
        if "chief audit" in role or "cae" in role:                    base = 5_000_000
        elif "vp" in role or "director" in role:                      base = 4_000_000
        elif "ai governance" in role or "ai audit" in role:           base = 3_500_000
        elif "manager" in role or "lead" in role:                     base = 2_800_000
        elif "senior" in role:                                         base = 1_800_000
        else:                                                          base = 1_400_000
        return base + min(exp * 100_000, 1_000_000)


def _compute_fair_model(
    skill_audit: List[Dict],
    resilience_score: int,
    annual_salary: int,
    market: str = "US",
) -> Dict[str, Any]:
    """
    FAIR Model adapted for career automation risk.

    TEF  = Threat Event Frequency = avg automation capability events per year
           (AI releases, automation tools, job function displacement events)
    Vuln = 1 - (resilience_score / 100)
           How exposed the user is to each TEF event
    SLE  = Single Loss Expectancy = fraction of salary at risk per displacement event
    ALE  = TEF × Vuln × SLE

    Conservative TEF = 6 events/year (6 significant AI capability jumps/year)
    based on observed pace: GPT-4 (2023), Claude 3 (2024), Gemini Ultra (2024),
    Copilot for Office (2024), etc.
    """
    if not skill_audit:
        declining_pct = 33
    else:
        declining = sum(1 for s in skill_audit if s["trajectory"] == "declining")
        declining_pct = declining / len(skill_audit) * 100

    # TEF: baseline 6/year; higher for high-declining-skill portfolios
    tef = round(4.0 + (declining_pct / 100) * 6.0, 1)

    # Vulnerability (0-1): inverse of resilience
    vulnerability = round(1.0 - (resilience_score / 100), 3)

    # SLE = fraction of salary exposed per event
    # Each automation event threatens roughly 8-15% of a role's task domains
    # Floor of 5% — even fully resilient roles have residual risk (role obsolescence, org restructure)
    exposed_fraction = max(0.05, min(0.60, declining_pct / 100 * 0.85))
    sle = int(annual_salary * exposed_fraction)

    # ALE
    ale = round(tef * vulnerability * sle)

    # Percentage of earnings at risk
    earnings_at_risk_pct = round(ale / annual_salary * 100, 1) if annual_salary else 0

    return {
        "tef":                   tef,
        "tef_label":             f"{tef} AI capability events per year",
        "vulnerability":         vulnerability,
        "vulnerability_label":   f"{round(vulnerability*100)}% exposure (resilience inverse)",
        "sle":                   sle,
        "sle_label":             f"${sle:,}/event" if market == "US" else f"₹{sle:,}/event",
        "ale":                   ale,
        "ale_label":             f"${ale:,}/year" if market == "US" else f"₹{ale:,}/year",
        "annual_salary_base":    annual_salary,
        "earnings_at_risk_pct":  earnings_at_risk_pct,
        "declining_skill_pct":   round(declining_pct, 1),
        "formula":               "ALE = TEF × Vulnerability × SLE",
        "interpretation": (
            "Critical — immediate career risk" if earnings_at_risk_pct >= 40 else
            "High — significant exposure, upskill within 12 months" if earnings_at_risk_pct >= 25 else
            "Moderate — manageable with targeted upskilling" if earnings_at_risk_pct >= 15 else
            "Low — portfolio is well-positioned for AI transition"
        ),
    }


def _classify_disruption(ale: float, salary: int, resilience_score: int) -> str:
    if salary == 0:
        pct = 0
    else:
        pct = ale / salary * 100
    if pct >= 40 or resilience_score < 25:   return "Critical"
    if pct >= 25 or resilience_score < 40:   return "High"
    if pct >= 15 or resilience_score < 55:   return "Moderate"
    return "Low"


def _build_year_forecast(
    base_mpi:          int,
    resilience_score:  int,
    certs:             List[str],
    skill_audit:       List[Dict],
    market:            str,
    exp_years:         int,
) -> List[Dict[str, Any]]:
    """
    5-year year-by-year disruption forecast.

    Models two scenarios:
      - Inaction: MPI drifts upward, resilience declines
      - Action:   MPI reduced by cert earning, resilience grows
    """
    current_year = datetime.utcnow().year
    forecast = []

    mpi_inaction    = float(base_mpi)
    mpi_action      = float(base_mpi)
    res_inaction    = float(resilience_score)
    res_action      = float(resilience_score)
    auto_multiplier = 1.0

    # Certs the user is most likely to earn next (based on gaps)
    recommended_certs = _recommended_cert_sequence(certs, skill_audit)

    year_phases = [
        ("Foundation",     "Lock in foundational AI governance cert. Eliminate top Declining skills."),
        ("Acceleration",   "Complete specialist cert. Build AI audit practice area leadership."),
        ("Differentiation","Publish thought leadership. Lead enterprise AI governance program."),
        ("Leadership",     "Target director/VP role. Chair AI governance committee or CAE role."),
        ("Mastery",        "Chief Audit Executive / AI Audit Director. Define industry standards."),
    ]

    for yr in range(1, 6):
        auto_multiplier *= _AUTOMATION_VELOCITY_PER_YEAR
        year_label = str(current_year + yr)

        # Inaction scenario: MPI drifts up, resilience drifts down
        mpi_inaction    = min(100, mpi_inaction + _MPI_DRIFT_PER_YEAR)
        res_inaction    = max(5,  res_inaction  - 3.5)

        # Action scenario: cert earned this year reduces MPI; skills developed add resilience
        cert_for_year   = recommended_certs[yr - 1] if yr <= len(recommended_certs) else None
        mpi_reduction   = _CERT_MPI_REDUCTION.get(cert_for_year, 5) if cert_for_year else 5
        mpi_action      = max(10, mpi_action + _MPI_DRIFT_PER_YEAR - mpi_reduction - 2)
        res_action      = min(95, res_action  + 6)

        # Primary risk for this year (automation multiplied over time)
        primary_risk    = _year_primary_risk(yr, auto_multiplier, skill_audit)

        phase_name, phase_goal = year_phases[yr - 1]

        forecast.append({
            "year":              yr,
            "year_label":        year_label,
            "phase":             phase_name,
            "goal":              phase_goal,
            "cert_target":       cert_for_year.upper() if cert_for_year else None,
            "primary_risk":      primary_risk,
            "automation_factor": round(auto_multiplier, 2),
            "mpi_inaction":      round(mpi_inaction),
            "mpi_action":        round(mpi_action),
            "resilience_inaction": round(res_inaction),
            "resilience_action":   round(res_action),
            "delta_mpi":           round(mpi_inaction - mpi_action),
            "key_actions": _year_actions(yr, cert_for_year, skill_audit, market),
            "milestone": _year_milestone(yr, exp_years, market),
        })

    return forecast


def _recommended_cert_sequence(
    held_certs: List[str],
    skill_audit: List[Dict],
) -> List[str]:
    """Priority-ordered cert sequence based on gaps."""
    declining_pct = sum(1 for s in skill_audit if s["trajectory"] == "declining") / max(len(skill_audit), 1)
    has_ai_cert   = any(c in held_certs for c in ("aigp", "aaia"))
    has_audit_cert = any(c in held_certs for c in ("cisa", "cissp"))

    seq = []
    if not has_ai_cert:
        seq.append("aigp")
        seq.append("aaia")
    else:
        seq.append("aaia" if "aigp" in held_certs else "aigp")

    if not has_audit_cert:
        seq.append("cisa")
    else:
        seq.append("ccsp")

    seq.extend(c for c in ["cism", "cissp", "ccsp", "crisc"] if c not in held_certs and c not in seq)
    return seq[:5]


def _year_primary_risk(yr: int, auto_multiplier: float, skill_audit: List[Dict]) -> str:
    declining = [s["skill"] for s in skill_audit if s["trajectory"] == "declining"]
    if yr == 1:
        return f"AI automates {declining[0] if declining else 'routine audit tasks'} — immediate exposure"
    if yr == 2:
        return f"AI expands into augmented tasks — {round(auto_multiplier * 15)}% more of your role automatable"
    if yr == 3:
        return "Generalist IT auditors face salary compression as AI handles standard workflows"
    if yr == 4:
        return "Only AI governance, ethics, and strategic roles command premium compensation"
    return "Automation plateau — but only AI-fluent leaders survive at the top quartile"


def _year_actions(yr: int, cert: Optional[str], skill_audit: List[Dict], market: str) -> List[str]:
    declining = [s["skill"] for s in skill_audit if s["trajectory"] == "declining"][:2]
    actions = []
    if cert:
        actions.append(f"Earn {cert.upper()} certification — reduces MPI by {_CERT_MPI_REDUCTION.get(cert, 5)} points")
    if declining and yr <= 2:
        actions.append(f"Phase out: {', '.join(declining)} — replace with AI-directed equivalents")
    if yr == 1:
        actions.append("Build AI audit portfolio: conduct first AI system risk assessment")
        if market == "IN":
            actions.append("Join ISACA India chapter — attend CISA/AIGP study groups in Bangalore/Mumbai")
    elif yr == 2:
        actions.append("Lead an AI governance initiative — document as case study for Board reporting")
    elif yr == 3:
        actions.append("Publish AI audit framework or white paper — build LinkedIn thought leadership")
    elif yr == 4:
        actions.append("Target Director/VP internal audit or CISO-adjacent role")
    elif yr == 5:
        actions.append("Position for CAE or AI Audit Director — define enterprise AI governance standards")
    return actions


def _year_milestone(yr: int, exp_years: int, market: str) -> str:
    total_exp = exp_years + yr
    if market == "US":
        milestones = {
            1: "AI-Augmented IT Audit Manager — $140K-$160K range",
            2: "AI Audit Manager / GRC Lead — $155K-$180K range",
            3: "Director of AI Audit / AI Governance Lead — $170K-$200K",
            4: "VP Internal Audit / AI Risk Director — $185K-$220K",
            5: "Chief Audit Executive / AI Audit Director — $200K-$250K+",
        }
    else:
        milestones = {
            1: "AI-Augmented IT Audit Manager — ₹28-35 LPA",
            2: "AI Audit Manager — ₹35-45 LPA",
            3: "Director of AI Audit — ₹45-60 LPA",
            4: "VP Internal Audit — ₹60-80 LPA",
            5: "Chief Audit Executive — ₹80-120 LPA",
        }
    return milestones.get(yr, f"Year {yr} milestone")


def _build_mitigation_plan(
    skill_audit:       List[Dict],
    certs:             List[str],
    resilience_score:  int,
    market:            str,
) -> List[Dict[str, Any]]:
    """Prioritised action plan ordered by urgency × impact."""
    actions = []
    priority = 1

    # Priority 1: Eliminating the highest-risk declining skills
    critical_declining = [
        s for s in skill_audit
        if s["trajectory"] == "declining" and s["automation_risk"] >= 80
    ]
    for skill in critical_declining[:3]:
        actions.append({
            "priority":  priority,
            "category":  "Skill Replacement",
            "action":    f"Phase out '{skill['skill']}' — {skill['automation_risk']}% automation risk within {skill['timeline_to_risk']}",
            "replace_with": "AI-directed workflow + governance oversight role",
            "impact":    "high",
            "timeline":  skill["timeline_to_risk"],
            "urgency":   "Immediate",
        })
        priority += 1

    # Priority 2: Cert gaps
    has_ai_cert = any(c in certs for c in ("aigp", "aaia"))
    if not has_ai_cert:
        actions.append({
            "priority":  priority,
            "category":  "Certification",
            "action":    "Earn AIGP (AI Governance Professional) — highest salary premium ($28K uplift)",
            "impact":    "high",
            "timeline":  "6-12 months",
            "urgency":   "High",
            "detail":    "AIGP appears in 38% of new IT Audit Manager JDs in 2026. Without it, you are invisible to a third of the market.",
        })
        priority += 1

    if "cisa" not in certs:
        actions.append({
            "priority":  priority,
            "category":  "Certification",
            "action":    "Earn CISA — foundational credential, appears in 78% of senior audit JDs",
            "impact":    "high",
            "timeline":  "6-9 months",
            "urgency":   "High" if resilience_score < 50 else "Medium",
        })
        priority += 1

    # Priority 3: Augmented skill upgrade
    augmented = [s for s in skill_audit if s["trajectory"] == "augmented"][:2]
    for skill in augmented:
        actions.append({
            "priority":  priority,
            "category":  "Skill Augmentation",
            "action":    f"Layer AI tools onto '{skill['skill']}' — become the human who directs AI in this domain",
            "impact":    "medium",
            "timeline":  "12-18 months",
            "urgency":   "Medium",
            "detail":    f"Automation risk: {skill['automation_risk']}%. Augmented approach extends viability to 2028+.",
        })
        priority += 1

    # Priority 4: Market presence
    actions.append({
        "priority":  priority,
        "category":  "Market Positioning",
        "action":    "Build AI audit thought leadership — publish case studies, join ISACA AI Working Group",
        "impact":    "medium",
        "timeline":  "Ongoing",
        "urgency":   "Low",
        "detail":    "Top-quartile AI audit leaders earn 25-35% more than median for equivalent roles.",
    })

    if market == "IN":
        actions.append({
            "priority":  priority + 1,
            "category":  "Market Positioning",
            "action":    "Target Big4 or BFSI sector — RBI/SEBI AI governance mandates create high demand in FY2026-27",
            "impact":    "high",
            "timeline":  "12-24 months",
            "urgency":   "High",
        })

    return actions


# ── FAIR Calculator (standalone) ────────────────────────────────────────────
# Used by /api/resilience/fair-calc for the interactive UI calculator.

def compute_fair_from_inputs(
    tef:             float,    # Threat Event Frequency per year
    vulnerability:   float,    # 0-1 (probability of loss given threat event)
    primary_loss:    int,      # direct loss per event ($)
    secondary_loss:  int = 0,  # indirect loss per event (reputation, regulatory) ($)
) -> Dict[str, Any]:
    """
    Standard FAIR calculation from raw user inputs.
    Used by the interactive 3-step FAIR Calculator in the dashboard.
    """
    sle = primary_loss + secondary_loss
    ale = round(tef * vulnerability * sle)

    return {
        "tef":            tef,
        "vulnerability":  vulnerability,
        "primary_loss":   primary_loss,
        "secondary_loss": secondary_loss,
        "sle":            sle,
        "ale":            ale,
        "risk_level": (
            "Critical"  if ale >= 500_000 else
            "High"      if ale >= 200_000 else
            "Medium"    if ale >= 50_000  else
            "Low"
        ),
        "interpretation": (
            f"ALE = ${ale:,}/year. "
            f"{'Immediate remediation required.' if ale >= 500_000 else 'Prioritise in next planning cycle.' if ale >= 200_000 else 'Schedule for next review cycle.' if ale >= 50_000 else 'Accept or monitor.'}"
        ),
        "formula_trace": (
            f"TEF={tef} × Vulnerability={vulnerability} × SLE=(${primary_loss:,}+${secondary_loss:,}) = ${ale:,}"
        ),
    }
