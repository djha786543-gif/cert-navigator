"""
Universal Architect Agent — Profile-driven cert recommendation engine.

Implements the "Diagnostic-to-Artifact" workflow:
  1. Analyze user profile (role, experience, certifications, skills)
  2. Score every cert by Difficulty (relative to user's gaps) + Market Value
  3. Return top 3 recommendations with known/gap topic breakdown and fit rationale

INPUT:  { "profile": dict }
OUTPUT: {
    "recommendations": [
        {
            "cert_id":            str,
            "cert":               dict,
            "difficulty_score":   int,    # 1–10 (10 = most challenging)
            "market_value_score": int,    # 1–10 (10 = highest salary uplift)
            "difficulty_label":   str,    # "Accessible" | "Moderate" | "Challenging"
            "fit_rationale":      str,    # Why this cert for this profile
            "known_topics":       list,   # Topics user likely already knows
            "gap_topics":         list,   # Priority study gaps
            "est_study_weeks":    str,
            "priority":           str,    # "immediate" | "midterm" | "longterm"
        },
        ...  # 3 items
    ],
    "profile_domain":  str,
    "profile_label":   str,
    "profile_summary": str,
}
"""
import logging
from typing import Any, Dict, List, Tuple

from .base_agent import AgentResult, BaseAgent, ResourceTier

logger = logging.getLogger(__name__)


# ── Cert-to-skills map — what does holding each cert signal? ──────────────────
# Used to reduce difficulty when the user already holds related credentials.

_CERT_SKILL_SIGNALS: Dict[str, List[str]] = {
    "cisa":  ["it audit", "internal controls", "sox", "isaca", "itgc", "cobit", "risk assessment", "information systems"],
    "cissp": ["security architecture", "cryptography", "access control", "network security", "risk management", "bcp", "drp"],
    "cism":  ["security management", "incident response", "risk management", "governance", "isaca"],
    "ccsp":  ["cloud security", "cloud architecture", "aws", "azure", "gcp", "data security", "iam", "casb"],
    "aigp":  ["ai governance", "ai risk", "nist ai rmf", "eu ai act", "model cards", "responsible ai", "iapp"],
    "crisc": ["risk management", "internal controls", "isaca", "risk assessment", "grc", "crisc"],
    "cgeit": ["it governance", "cobit", "enterprise governance", "isaca"],
    "cipp":  ["gdpr", "privacy", "data protection", "iapp", "ccpa"],
    "cipm":  ["privacy management", "gdpr", "data governance", "iapp", "privacy program"],
    "pmp":   ["project management", "agile", "stakeholder management", "scrum", "pmi", "pmbok"],
    "aws_ml": ["aws", "sagemaker", "machine learning", "mlops", "tensorflow", "pytorch"],
    "ckad":  ["kubernetes", "docker", "containers", "devops", "cloud native"],
    "aws_saa": ["aws", "cloud architecture", "ec2", "s3", "vpc", "lambda"],
    "cfa_l1": ["cfa", "financial analysis", "equity", "fixed income", "portfolio management"],
    "frm_p1": ["risk management", "frm", "var", "derivatives", "market risk", "basel"],
    "aaia":  ["ai audit", "ai risk", "audit", "ai governance"],
    "ciasp": ["information assurance", "security", "incident response", "risk"],
}

# ── Known-topic profiles per cert — for gap analysis ─────────────────────────
# These are the "baseline" topics a user should know if they pass the cert.

_CERT_KNOWN_TOPICS: Dict[str, List[str]] = {
    "cisa":  ["Risk-based audit methodology", "ITGC design & testing", "Evidence gathering", "Audit reporting", "SDLC controls", "Change management controls"],
    "cissp": ["CIA triad", "Cryptography & PKI", "Network security architecture", "BCP / DRP", "Access control models", "Physical security"],
    "cism":  ["IS risk assessment", "Security incident management", "IS governance frameworks", "Security program strategy", "Third-party risk"],
    "ccsp":  ["Shared responsibility model", "Cloud architecture patterns", "CASB controls", "CSP contract review", "Cloud data classification", "Encryption key management"],
    "aigp":  ["AI risk tiers (EU AI Act)", "NIST AI RMF (GOVERN-MAP-MEASURE-MANAGE)", "Model governance lifecycle", "Bias / fairness metrics", "AI audit methodology", "Foundation model risks"],
    "crisc": ["Risk identification & assessment", "Risk response planning", "Control design & testing", "Risk register maintenance", "RACI for risk governance"],
    "pmp":   ["Project lifecycle phases", "WBS decomposition", "Earned Value Management", "Stakeholder register", "Risk register", "Integrated change control"],
    "aws_ml": ["SageMaker pipeline", "Feature engineering", "Model evaluation metrics", "MLOps / model monitoring", "Responsible AI on AWS", "VPC security for ML"],
    "ckad":  ["Pod & deployment design", "ConfigMaps & Secrets", "Services & Ingress", "Namespace isolation", "Health probes", "RBAC"],
    "ccsp":  ["Shared responsibility model", "Cloud architecture patterns", "CASB controls", "Encryption key management (BYOK/HYOK)", "Forensics in cloud", "CSP legal jurisdiction"],
    "cfa_l1": ["Time value of money", "IFRS vs GAAP", "Equity valuation (DCF)", "Fixed income pricing", "Portfolio theory (CAPM)", "Ethics Standards of Practice"],
    "frm_p1": ["Value at Risk (VaR)", "Basel III capital requirements", "Options / derivatives pricing", "Market risk models", "Credit risk basics", "Monte Carlo simulation"],
    "aaia":  ["AI technology fundamentals", "AI risk assessment", "AI audit methodology", "AI governance controls"],
    "ciasp": ["Security risk management", "Security architecture", "Security operations", "Incident response"],
}

# ── Base difficulty per cert (1–10, pre-profile adjustment) ──────────────────
# Reflects exam complexity, domain breadth, and question count.

_CERT_DIFFICULTY_BASE: Dict[str, int] = {
    "aigp":   5,   # Moderate — conceptual, 90Q, newer domain
    "cisa":   7,   # Hard — 150Q, 4h, technical breadth
    "ccsp":   8,   # Hard — 125Q, 6 broad cloud domains
    "aaia":   4,   # Moderate — emerging, 100Q
    "ciasp":  5,   # Moderate — 120Q
    "cissp":  9,   # Very hard — 125–175Q CAT, 8 domains
    "cism":   7,   # Hard — 150Q, strategy focus
    "crisc":  7,   # Hard — 150Q, risk methodology
    "cgeit":  7,
    "pmp":    6,   # Moderate-hard — 180Q, broad
    "aws_ml": 7,
    "ckad":   7,   # Performance-based
    "aws_saa": 6,
    "cfa_l1": 9,   # Very hard — 180Q, 300h study average
    "frm_p1": 8,
    "cipp":   5,
    "cipm":   5,
    "cphq":   6,
    "chda":   5,
    "gcp_research": 3,
    "citi_research": 3,
    "nih_grant": 4,
    "bioinformatics_cert": 6,
    "tensorflow_dev": 6,
    "azure_ds": 6,
    "csm":    3,
}


def _calc_difficulty(cert_id: str, profile: Dict[str, Any]) -> int:
    """
    Compute difficulty score 1–10 for a cert given a user's profile.
    Lower score = more accessible for this particular user.
    Reduces base difficulty when the user has matching skills / certs.
    """
    base = _CERT_DIFFICULTY_BASE.get(cert_id, 6)

    # Build a combined text blob of the user's existing knowledge signals
    skills_text = " ".join(str(s) for s in profile.get("skills", [])).lower()
    role_text   = (profile.get("current_role") or profile.get("target_role") or "").lower()
    summary     = (profile.get("summary") or "").lower()
    combined    = f"{skills_text} {role_text} {summary}"

    # Current certs as a set of lower-case strings
    user_certs = {c.lower().replace(" ", "_") for c in profile.get("certifications", []) if isinstance(c, str)}

    # Count how many skill signals for this cert the user already has
    related_signals = _CERT_SKILL_SIGNALS.get(cert_id, [])
    skill_hits = sum(1 for sig in related_signals if sig.lower() in combined)

    # Direct cert overlap: does the user hold this cert or a closely related one?
    direct_match = cert_id.lower() in user_certs

    # Reduction: up to 3 points off base
    reduction = min(3, skill_hits // 2 + (2 if direct_match else 0))

    return max(1, min(10, base - reduction))


def _calc_market_value(cert: Dict[str, Any]) -> int:
    """
    Market value score 1–10.
    Based on salary_premium_usd (max $40K → 10) + demand signal boost.
    """
    premium = cert.get("salary_premium_usd", 0) or 0
    demand  = (cert.get("demand_signal") or "Medium").lower()

    # Normalise: $4K per point, capped at 10
    score = min(10, max(1, round(premium / 4_000)))

    # Demand signal fine-tuning
    if demand == "critical":
        score = min(10, score + 1)
    elif demand in ("emerging", "medium"):
        score = max(1, score - 1)

    return score


def _get_known_gap_topics(cert_id: str, profile: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    """
    Return (known_topics, gap_topics) by comparing cert's expected topics
    against the user's skills / experience text.
    """
    all_topics = _CERT_KNOWN_TOPICS.get(cert_id, [])
    if not all_topics:
        return [], []

    skills_text  = " ".join(str(s) for s in profile.get("skills", [])).lower()
    role_text    = (profile.get("current_role") or "").lower()
    summary      = (profile.get("summary") or "").lower()
    user_certs   = " ".join(profile.get("certifications", [])).lower()
    combined     = f"{skills_text} {role_text} {summary} {user_certs}"

    known: List[str] = []
    gaps:  List[str] = []
    for topic in all_topics:
        # Tokenise topic words to check presence in combined text
        words = [w.lower() for w in topic.replace("/", " ").replace("-", " ").replace("(", "").replace(")", "").split()]
        # Consider "known" if at least 2 words appear in the combined profile blob
        hits = sum(1 for w in words if len(w) > 3 and w in combined)
        if hits >= 2:
            known.append(topic)
        else:
            gaps.append(topic)

    return known[:3], gaps[:4]  # cap for readability


def _fit_rationale(cert: Dict[str, Any], profile: Dict[str, Any], difficulty: int, market_value: int) -> str:
    """Generate a focused 1-sentence rationale for this cert × profile match."""
    acronym     = cert.get("acronym") or cert.get("id", "").upper()
    role        = profile.get("current_role") or profile.get("target_role") or "your current role"
    premium     = cert.get("salary_premium_usd") or 0
    demand      = cert.get("demand_signal") or "High"
    trend       = cert.get("trend") or ""

    premium_str  = f"+${premium:,} salary uplift" if premium else "strong salary uplift"
    diff_label   = "accessible" if difficulty <= 3 else "moderate" if difficulty <= 6 else "challenging but high-reward"
    trend_suffix = f" · {trend}" if trend else ""

    return (
        f"For {role}: {acronym} is a {diff_label} path with {premium_str} "
        f"and {demand.lower()} market demand{trend_suffix}."
    )


def _build_profile_summary(profile: Dict[str, Any]) -> str:
    """One-sentence human-readable profile digest."""
    role  = profile.get("current_role") or profile.get("target_role") or "Professional"
    yoe   = profile.get("years_experience") or 0
    certs = profile.get("certifications") or []
    certs_str = ", ".join(str(c) for c in certs[:3]) if certs else "no certifications on file"
    yoe_str   = f"{yoe}+ years experience" if yoe else "experience unspecified"
    return f"{role} — {yoe_str} — credentials: {certs_str}."


class UniversalArchitectAgent(BaseAgent):
    """
    Universal Architect — the 'Diagnostic-to-Artifact' recommendation engine.

    Analyzes any user profile and returns 3 tailored cert paths ranked by:
      • Market Value Score  (salary uplift + demand signal)
      • Difficulty Score    (gap between current skills and cert requirements)
      • Known vs. Gap topic breakdown for profile-aware artifact generation
    """

    name = "universal_architect_agent"
    resource_tier = ResourceTier.LIGHT

    async def _execute(self, input_data: Dict[str, Any]) -> AgentResult:
        from src.backend.agents.artifact_sovereign_agent import CERT_CATALOG
        from src.backend.engine.domain_classifier import (
            classify, domain_label, get_domain_cert_catalog,
        )

        profile = input_data.get("profile", {})
        result  = AgentResult(success=False, agent_name=self.name)

        # Detect primary domain for profile context
        domain = classify(profile)

        # Build full candidate pool: hardcoded certs + domain-specific certs
        candidates: List[Dict[str, Any]] = []
        seen_ids: set = set()

        for cert in CERT_CATALOG.values():
            cid = cert["id"]
            if cid not in seen_ids:
                candidates.append(cert)
                seen_ids.add(cid)

        for cert in get_domain_cert_catalog(domain):
            cid = cert["id"]
            if cid not in seen_ids:
                candidates.append({
                    "id":               cid,
                    "name":             cert["name"],
                    "acronym":          cert.get("acronym", cid.upper()),
                    "issuer":           cert.get("issuer", ""),
                    "exam_questions":   cert.get("exam_questions", 40),
                    "passing_score":    cert.get("passing_score", 70),
                    "duration_mins":    cert.get("duration_mins", 90),
                    "salary_premium_usd": cert.get("salary_premium_usd", 0),
                    "demand_signal":    (cert.get("priority") or "high").capitalize(),
                    "trend":            cert.get("trend", "Rising"),
                    "domains":          cert.get("domains", []),
                    "study_weeks":      cert.get("study_weeks", "8–12 weeks"),
                })
                seen_ids.add(cid)

        # Certs already held — skip these
        user_certs_lower = {
            c.lower().replace(" ", "_")
            for c in profile.get("certifications", []) if isinstance(c, str)
        }

        # Score candidates
        scored: List[Dict[str, Any]] = []
        for cert in candidates:
            cid = cert["id"]
            if cid.lower() in user_certs_lower:
                continue
            if cert.get("acronym", "").lower().replace(" ", "_") in user_certs_lower:
                continue

            difficulty    = _calc_difficulty(cid, profile)
            market_value  = _calc_market_value(cert)
            known, gaps   = _get_known_gap_topics(cid, profile)
            rationale     = _fit_rationale(cert, profile, difficulty, market_value)

            # Composite recommendation score: value-first, penalise excessive difficulty
            rec_score = (market_value * 2) - difficulty

            est_weeks = cert.get("study_weeks") or (
                "4–8 weeks"  if difficulty <= 3 else
                "8–12 weeks" if difficulty <= 6 else
                "12–20 weeks"
            )
            priority = (
                "immediate" if difficulty <= 4 else
                "midterm"   if difficulty <= 7 else
                "longterm"
            )
            diff_label = (
                "Accessible"  if difficulty <= 3 else
                "Moderate"    if difficulty <= 6 else
                "Challenging"
            )

            scored.append({
                "cert_id":            cid,
                "cert":               cert,
                "difficulty_score":   difficulty,
                "market_value_score": market_value,
                "difficulty_label":   diff_label,
                "fit_rationale":      rationale,
                "known_topics":       known,
                "gap_topics":         gaps,
                "est_study_weeks":    est_weeks,
                "priority":           priority,
                "_rec_score":         rec_score,
            })

        if not scored:
            result.error = "No cert recommendations could be generated for this profile."
            return result

        scored.sort(key=lambda x: x["_rec_score"], reverse=True)
        top3 = scored[:3]
        for r in top3:
            r.pop("_rec_score", None)

        result.data = {
            "recommendations": top3,
            "profile_domain":  domain,
            "profile_label":   domain_label(domain),
            "profile_summary": _build_profile_summary(profile),
        }
        result.success = True
        return result
