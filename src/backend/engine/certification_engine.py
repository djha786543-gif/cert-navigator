"""
Phase 3 – Certification Recommendation Engine

Reads the Gold Standard certifications_catalog.json and produces:
  1. Tiered recommendations (Immediate / Mid-term / Long-term) based on the user's
     current certifications, skills, experience, and target role.
  2. A progress tracker that stores domain-level completion scores and unlocks
     the next certification once current ones are completed.
  3. Per-certification study packs (domains, labs, questions) matching AAIA/CIASP depth.
"""
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

# ── Locate catalog ─────────────────────────────────────────────────────────────
_CATALOG_PATH = Path(__file__).resolve().parents[3] / "data" / "certifications_catalog.json"


def _load_catalog() -> Dict[str, Any]:
    with open(_CATALOG_PATH, encoding="utf-8") as f:
        return json.load(f)


# ── Public API ─────────────────────────────────────────────────────────────────

def get_recommendations(profile: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate tiered certification recommendations for a user profile.
    Routes through the domain classifier so every profile — IT Auditor,
    Research Scientist, ML Engineer, Finance Analyst, etc. — receives
    recommendations relevant to their actual domain.

    Returns:
        {
          "domain":       str,   # detected domain key
          "immediate":   [...],  # 0-12 months
          "midterm":     [...],  # 12-24 months
          "longterm":    [...],  # 24-48 months
          "path":        {...},  # recommended career path
          "already_held": [...]  # confirmed existing certifications
        }
    """
    from src.backend.engine.domain_classifier import (
        classify as classify_domain,
        get_domain_cert_catalog,
        domain_label,
    )

    domain = classify_domain(profile)

    # Non-IT-audit domains use the multi-domain catalog from domain_classifier
    if domain != "it_audit":
        return _get_domain_recommendations(profile, domain, get_domain_cert_catalog(domain))

    # IT audit domain: use the rich certifications_catalog.json
    catalog      = _load_catalog()
    all_certs    = {c["id"]: c for c in catalog["certifications"]}
    held_ids     = _extract_held_cert_ids(profile, all_certs)
    role_context = _analyse_role(profile)

    recommendations = {
        "domain":       domain,
        "domain_label": domain_label(domain),
        "immediate":    [],
        "midterm":      [],
        "longterm":     [],
        "already_held": held_ids,
    }

    for cert_id, cert in all_certs.items():
        if cert_id in held_ids:
            continue
        prereqs = cert.get("prerequisite_certs", [])
        if prereqs and not all(p in held_ids for p in prereqs):
            continue
        enriched = _enrich_cert(cert, profile, held_ids, role_context)
        tier = cert.get("tier", "longterm")
        recommendations[tier].append(enriched)

    for tier in ("immediate", "midterm", "longterm"):
        recommendations[tier].sort(key=lambda c: c["priority_score"], reverse=True)

    paths = catalog.get("certification_paths", {})
    recommendations["path"] = paths.get(
        "it_audit_to_ai_audit_director",
        next(iter(paths.values()), {})
    )
    return recommendations


def _get_domain_recommendations(
    profile: Dict[str, Any],
    domain: str,
    cert_catalog: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Build tiered cert recommendations from the domain-specific catalog.
    Scores each cert by relevance to the profile's skills and experience.
    """
    from src.backend.engine.domain_classifier import domain_label

    user_skills = {s.lower() for s in profile.get("skills", [])}
    exp_years   = profile.get("experience_years") or 0

    # Extract held cert IDs from profile
    held = set()
    for pc in profile.get("certifications", []):
        name = (pc.get("name", pc) if isinstance(pc, dict) else str(pc)).upper()
        for cert in cert_catalog:
            if cert["acronym"].upper() in name or cert["id"].upper() in name:
                held.add(cert["id"])

    recs: Dict[str, List] = {"immediate": [], "midterm": [], "longterm": []}

    for cert in cert_catalog:
        if cert["id"] in held:
            continue

        # Score: skill overlap + seniority fit
        cert_topics = " ".join(
            " ".join(d.get("topics", [])) for d in cert.get("domains", [])
        ).lower()
        matched = [s for s in user_skills if s in cert_topics]
        score   = len(matched) * 5

        base_priority = {"critical": 100, "high": 75, "medium": 50, "low": 25}
        score += base_priority.get(cert.get("priority", "medium"), 50)

        # Seniority: senior-level certs boosted for experienced users
        if exp_years >= 6 and any(
            w in cert.get("name", "").lower()
            for w in ["senior", "principal", "director", "lead", "specialist", "advanced"]
        ):
            score += 15

        tier = cert.get("tier", "midterm")
        recs[tier].append({
            **cert,
            "priority_score":   min(score, 100),
            "personalised_why": (
                [f"Builds on your existing: {', '.join(matched[:3])}"] if matched
                else [cert.get("rationale", "")]
            ),
        })

    for tier in ("immediate", "midterm", "longterm"):
        recs[tier].sort(key=lambda c: c["priority_score"], reverse=True)

    return {
        "domain":       domain,
        "domain_label": domain_label(domain),
        "immediate":    recs["immediate"],
        "midterm":      recs["midterm"],
        "longterm":     recs["longterm"],
        "already_held": list(held),
        "path": {
            "title":       f"{domain_label(domain)} Career Path",
            "description": f"Recommended certification sequence for {domain_label(domain)} professionals.",
            "steps":       [c["acronym"] for c in cert_catalog[:4]],
        },
    }


def get_cert_detail(cert_id: str) -> Dict[str, Any]:
    """Return full Gold Standard detail for a single certification."""
    catalog   = _load_catalog()
    certs_map = {c["id"]: c for c in catalog["certifications"]}
    cert      = certs_map.get(cert_id)
    if not cert:
        raise ValueError(f"Certification '{cert_id}' not found in catalog")
    return cert


def get_study_pack(cert_id: str) -> Dict[str, Any]:
    """
    Return a focused study pack for a certification:
      - Domain breakdown with weights and topics
      - Recommended labs (ordered by difficulty)
      - Practice questions
      - Study resources
    """
    cert = get_cert_detail(cert_id)
    return {
        "cert_id":    cert_id,
        "name":       cert["name"],
        "acronym":    cert["acronym"],
        "issuer":     cert["issuer"],
        "exam_info":  cert["exam"],
        "domains":    cert["domains"],
        "labs":       cert.get("labs", []),
        "questions":  cert.get("practice_questions", []),
        "resources":  cert.get("study_resources", {}),
    }


def get_progress(profile: Dict[str, Any], progress_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate domain-level progress for each in-progress certification.

    progress_data format:
        {
          "aigp": {
            "aigp-d1": 80,   # % complete for each domain
            "aigp-d2": 45,
            ...
          },
          ...
        }

    Returns enriched progress with:
      - overall_pct per cert
      - unlock status of next cert
      - study recommendations based on weakest domains
    """
    catalog   = _load_catalog()
    certs_map = {c["id"]: c for c in catalog["certifications"]}
    result    = {}

    for cert_id, domain_scores in progress_data.items():
        cert = certs_map.get(cert_id)
        if not cert:
            continue

        domains       = cert["domains"]
        total_weight  = sum(d["weight_pct"] for d in domains)
        weighted_pct  = 0.0

        domain_status = []
        for domain in domains:
            did    = domain["id"]
            score  = domain_scores.get(did, 0)
            weight = domain["weight_pct"]
            weighted_pct += score * (weight / total_weight)
            domain_status.append({
                "id":       did,
                "name":     domain["name"],
                "weight":   weight,
                "progress": score,
                "status":   _progress_label(score),
            })

        overall = round(weighted_pct, 1)
        ready   = overall >= 80

        # Weakest domain = study focus
        weakest = min(domain_status, key=lambda d: d["progress"])

        result[cert_id] = {
            "cert_name":    cert["name"],
            "acronym":      cert["acronym"],
            "overall_pct":  overall,
            "exam_ready":   ready,
            "domains":      domain_status,
            "study_focus":  weakest["name"],
            "unlocks_next": _get_unlocked_certs(cert_id, overall, certs_map),
        }

    return result


def update_domain_progress(
    progress_data: Dict[str, Any],
    cert_id: str,
    domain_id: str,
    new_score: int,
) -> Dict[str, Any]:
    """Update a domain score (0–100) and return the updated progress dict."""
    if cert_id not in progress_data:
        progress_data[cert_id] = {}
    progress_data[cert_id][domain_id] = max(0, min(100, new_score))
    return progress_data


# ── Internal helpers ───────────────────────────────────────────────────────────

def _extract_held_cert_ids(profile: Dict[str, Any], all_certs: Dict[str, Any]) -> List[str]:
    """
    Match profile certifications against catalog IDs.
    If a cert is not in the catalog (e.g. CISA), store its acronym directly
    so it can still satisfy prerequisite checks.
    """
    held = set()
    profile_certs = profile.get("certifications", [])
    for pc in profile_certs:
        name = (pc.get("name", pc) if isinstance(pc, dict) else str(pc)).upper()
        matched = False
        for cid, cert in all_certs.items():
            if cert["acronym"].upper() in name or cid.upper() in name:
                held.add(cid)
                matched = True
        if not matched:
            # Store the bare acronym (first token before any space/parenthesis)
            acronym = name.split()[0].rstrip("(").strip()
            held.add(acronym.lower())
    return list(held)


def _analyse_role(profile: Dict[str, Any]) -> Dict[str, Any]:
    target  = (profile.get("target_role") or "").lower()
    current = (profile.get("current_role") or "").lower()
    exp     = profile.get("experience_years") or 0
    return {
        "is_senior":     exp >= 8 or "director" in target or "executive" in current,
        "is_ai_focused": any(w in target for w in ["ai", "artificial", "machine", "governance"]),
        "is_cloud":      any(w in target for w in ["cloud", "aws", "azure", "gcp"]),
        "is_cae_track":  any(w in target for w in ["cae", "chief", "director", "executive"]),
    }


def _enrich_cert(
    cert: Dict[str, Any],
    profile: Dict[str, Any],
    held_ids: List[str],
    role_context: Dict[str, Any],
) -> Dict[str, Any]:
    """Add a priority_score and personalised rationale to a cert dict."""
    base      = {"critical": 100, "high": 75, "medium": 50, "low": 25}
    score     = base.get(cert.get("priority", "medium"), 50)
    user_skills = {s.lower() for s in profile.get("skills", [])}
    rationale   = []

    # Boost if cert domains match user skills
    domain_keywords = " ".join(
        " ".join(d.get("topics", [])) for d in cert.get("domains", [])
    ).lower()
    matched_skills = [s for s in user_skills if s in domain_keywords]
    if matched_skills:
        score   += len(matched_skills) * 3
        rationale.append(f"Builds on your existing: {', '.join(matched_skills[:3])}")

    # Role boosts
    if role_context["is_ai_focused"] and cert["id"] in ("aigp", "aaism"):
        score += 20
        rationale.append("Directly aligns with your AI-focused target role")
    if role_context["is_cloud"] and cert["id"] == "ccsp":
        score += 20
        rationale.append("Cloud security is core to your target role")
    if role_context["is_cae_track"] and cert["id"] in ("cgeit", "crisc"):
        score += 15
        rationale.append("Expected at Director / CAE level")

    return {
        **cert,
        "priority_score":   min(score, 100),
        "personalised_why": rationale or [cert.get("career_impact", "")],
    }


def _progress_label(pct: float) -> str:
    if pct == 0:    return "not_started"
    if pct < 40:    return "early"
    if pct < 70:    return "in_progress"
    if pct < 90:    return "near_ready"
    return "ready"


def _get_unlocked_certs(
    completed_id: str,
    overall_pct: float,
    certs_map: Dict[str, Any],
) -> List[str]:
    """Return list of cert IDs that become available when this cert is completed (>= 80%)."""
    if overall_pct < 80:
        return []
    return [
        cid
        for cid, cert in certs_map.items()
        if completed_id in cert.get("prerequisite_certs", [])
    ]
