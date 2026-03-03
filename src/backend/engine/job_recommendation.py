"""
Phase 8C — Multi-Market Job Recommendation Engine (async, upgraded)

Architecture:
  asyncio.gather() fetches from 6+ sources simultaneously:
    1. Adzuna        — US primary (250 req/day free tier)
    2. Reed.co.uk    — India/UK market (150 req/day free)
    3. JSearch       — RapidAPI backup (500 req/month free)
    4. USAJobs.gov   — Federal IT audit roles (free, no key)
    5. ISACA RSS     — Niche cert-specific job board (RSS, no key)
    6. Indeed RSS    — General market signal (RSS, no key)
  All sources run in parallel; total latency = max(individual) not sum.

Phase 8C Upgrades:
  - Hire-Probability Score (0-100) replaces simple match_score:
      Cert match (40%) + Skill overlap % (30%) + Seniority fit (20%) + Market velocity (10%)
  - Top 10 PRIORITY flag: highest hire_probability jobs tagged "PRIORITY"
  - Filter params: remote (bool), location (str), salary_min (int)
  - USAJobs.gov, ISACA RSS, Indeed RSS added as zero-API-key sources

Markets:
  "US" → Adzuna US + USAJobs + ISACA RSS + Indeed RSS + JSearch + curated mock
  "IN" → Reed India + Adzuna IN + ISACA RSS + curated mock

⚠️ CAPACITY FLAGS:
  - Adzuna free: 250 req/day → saturates at ~84 users @ 3 calls/user
    Mitigation: Cache per-user results for 6 hours (APScheduler refresh)
  - RSS feeds: no rate limit; parsed client-side, ~50ms per feed
  - USAJobs: free, no rate limit, 100 results/page
"""
import asyncio
import logging
import os
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

# ── API credentials ────────────────────────────────────────────────────────
ADZUNA_APP_ID  = os.getenv("ADZUNA_APP_ID",  "")
ADZUNA_APP_KEY = os.getenv("ADZUNA_APP_KEY", "")
REED_API_KEY   = os.getenv("REED_API_KEY",   "")
JSEARCH_API_KEY = os.getenv("JSEARCH_API_KEY", "")

_ADZUNA_US  = "https://api.adzuna.com/v1/api/jobs/us/search/1"
_ADZUNA_IN  = "https://api.adzuna.com/v1/api/jobs/in/search/1"
_REED_BASE  = "https://www.reed.co.uk/api/1.0/search"
_JSEARCH    = "https://jsearch.p.rapidapi.com/search"
_USAJOBS       = "https://data.usajobs.gov/api/search"
_ISACA_RSS     = "https://www.isaca.org/rss/jobs"
_INDEED_RSS    = "https://www.indeed.com/rss?q={query}&l={location}&sort=date"
# Phase 8D: Research/Academic job sources
_NATURE_RSS    = "https://www.nature.com/naturecareers/rss/jobs"
_SCIENCE_RSS   = "https://jobs.sciencecareers.org/rss/jobs/?k={query}"
_LINKEDIN_RSS  = "https://www.linkedin.com/jobs/search/?keywords={role}&location={loc}&f_TPR=r86400&format=rss"
_NAUKRI_API    = "https://www.naukri.com/jobapi/v3/search?noOfResults=10&urlType=search_by_keyword&searchType=adv&keyword={role}&k={role}&l=&experience=0&salary=0&industry=IT+Software&domain=IT%20Software"
_USAJOBS_RESEARCH_SERIES = ["1301", "1320", "1530", "0110"]  # Research/Science OPM series

# Research role keywords (for automatic source routing)
_RESEARCH_ROLE_SIGNALS = [
    "research", "post-doc", "postdoc", "postdoctoral", "professor",
    "principal investigator", "lab manager", "clinical researcher",
    "scientist", "research associate",
]

# Seniority level signals in job titles / descriptions
_SENIORITY_PATTERNS = [
    (["chief", "cae", "vp ", "vice president", "executive director"], 15),
    (["director", "head of"],                                          12),
    (["senior manager", "sr. manager"],                                 9),
    (["manager", "lead", "principal"],                                  6),
    (["senior", "sr.", "senior analyst"],                               4),
    (["analyst", "associate", "specialist", "junior"],                  1),
]

# ── JD keyword analysis weights (for trending skill detection) ─────────────
_SKILL_SIGNALS = {
    # Signals weighted by 2026 US/India hiring trend velocity
    "ai governance":    {"us": 42, "in": 35, "trajectory": "rising"},
    "nist ai rmf":      {"us": 38, "in": 25, "trajectory": "rising"},
    "eu ai act":        {"us": 30, "in": 28, "trajectory": "rising"},
    "aigp":             {"us": 35, "in": 30, "trajectory": "rising"},
    "zero trust":       {"us": 28, "in": 22, "trajectory": "rising"},
    "ccsp":             {"us": 25, "in": 30, "trajectory": "rising"},
    "cloud security":   {"us": 22, "in": 35, "trajectory": "rising"},
    "model risk":       {"us": 30, "in": 20, "trajectory": "rising"},
    "python":           {"us": 18, "in": 25, "trajectory": "stable"},
    "servicenow":       {"us": 15, "in": 22, "trajectory": "stable"},
    "cisa":             {"us": 20, "in": 32, "trajectory": "stable"},
    "sox auditing":     {"us": 12, "in": 18, "trajectory": "stable"},
    "manual sampling":  {"us": -15, "in": -10, "trajectory": "declining"},
    "spreadsheet audit":{"us": -20, "in": -15, "trajectory": "declining"},
    "basic excel":      {"us": -18, "in": -12, "trajectory": "declining"},
}


# ── Broaden-to-Narrow role mapping ─────────────────────────────────────────
# Maps verbose or hyper-specific job titles to shorter, API-friendly search terms.
# Ordered from most specific to most general; first match wins.
_ROLE_BROADENING: List[tuple] = [
    # IT Audit / GRC track
    (["chief audit executive", "head of audit", "cae "],          "Chief Audit Executive"),
    (["it audit manager", "audit manager", "audit lead"],         "IT Audit Manager"),
    (["it auditor", "is auditor", "information systems auditor"], "IT Auditor"),
    (["ai governance", "ai audit", "ai risk"],                    "AI Governance"),
    (["sox itgc", "sox audit", "itgc"],                           "IT Audit SOX"),
    (["cloud security audit", "cloud audit"],                     "Cloud Security Auditor"),
    (["grc manager", "grc lead", "governance risk"],              "GRC Manager"),
    (["model risk", "model validation"],                          "Model Risk"),
    (["it risk", "information risk"],                             "IT Risk Manager"),
    (["internal audit", "internal auditor"],                      "Internal Auditor"),
    # Cybersecurity
    (["cissp", "cism", "security manager", "information security manager"], "Information Security Manager"),
    (["security analyst", "soc analyst"],                         "Security Analyst"),
    (["penetration tester", "pentester", "red team"],             "Penetration Tester"),
    # Research / Academic track
    (["principal investigator", " pi "],                          "Principal Investigator"),
    (["postdoctoral", "post-doctoral", "post-doc", "postdoc"],    "Research Scientist"),
    (["research scientist", "research fellow"],                   "Research Scientist"),
    (["research associate", "research assistant"],                "Research Associate"),
    (["biomedical", "bio-medical", "biomedical engineer"],        "Biomedical Researcher"),
    (["clinical researcher", "clinical research coordinator"],    "Clinical Research"),
    (["lab manager", "laboratory manager"],                       "Lab Manager"),
    (["professor", "assistant professor", "associate professor"], "Professor Research"),
    # Technology
    (["data scientist", "machine learning engineer", "ml engineer"], "Data Scientist"),
    (["data analyst", "business analyst", "bi analyst"],          "Data Analyst"),
    (["software engineer", "software developer", "swe"],          "Software Engineer"),
    (["devops engineer", "site reliability", "sre"],              "DevOps Engineer"),
    (["cloud engineer", "cloud architect"],                       "Cloud Engineer"),
    (["product manager", "product lead"],                         "Product Manager"),
    # Finance
    (["financial analyst", "finance analyst", "fp&a"],            "Financial Analyst"),
    (["controller", "accounting manager"],                        "Controller"),
]


def _broaden_role(role: str) -> str:
    """
    Broaden-to-Narrow: strip verbose modifiers and map to a concise API search term.

    Examples:
      "IT Audit Manager – AI & Emerging Tech (Senior)"  → "IT Audit Manager"
      "Postdoctoral Researcher in Biomedical Engineering" → "Research Scientist"
      "Chief Audit Executive / VP Internal Audit"        → "Chief Audit Executive"
    Falls back to first 3 words of the original title for unknown roles.
    """
    role_lower = role.lower()
    for patterns, broad_term in _ROLE_BROADENING:
        if any(p in role_lower for p in patterns):
            return broad_term
    # Fallback: truncate to 3 words (removes parenthetical modifiers)
    words = role.split()
    return " ".join(words[:3]) if len(words) > 3 else role


# ── Public async API ───────────────────────────────────────────────────────
async def recommend_jobs_async(
    profile: Dict[str, Any],
    market: str = "US",
    max_results: int = 15,
    remote: Optional[bool] = None,
    location: Optional[str] = None,
    salary_min: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Fetch, merge, score, and return job recommendations.
    Phase 8C: hire-probability scoring, new sources, filter params.

    Filter params (all optional):
      remote      — True = remote-only, False = on-site only, None = all
      location    — city/state string filter on job location
      salary_min  — minimum salary_min threshold

    Returns:
      {
        "jobs": [...],          # sorted by hire_probability DESC, top 10 flagged PRIORITY
        "market": "US"|"IN",
        "sources_used": [...],
        "market_intelligence": { trending_skills, declining_skills, ... }
      }
    """
    role_raw = profile.get("target_role") or profile.get("current_role") or "IT Audit"
    role     = _broaden_role(role_raw)   # Broaden-to-Narrow: strip verbose modifiers
    mkt      = market.upper()

    # Phase 8D: Detect research/academic track
    is_research = any(sig in role.lower() for sig in _RESEARCH_ROLE_SIGNALS)

    # Secondary Adzuna query: domain-appropriate alt role for broader coverage
    try:
        from src.backend.engine.domain_classifier import (
            classify as _classify_domain,
            get_domain_alt_search as _domain_alt_search,
        )
        _domain = _classify_domain(profile)
        role_alt = _domain_alt_search(_domain)
    except Exception:
        role_alt = ""

    async with httpx.AsyncClient(timeout=httpx.Timeout(8.0, connect=3.0)) as client:
        # Parallel fetch from all available sources
        gather_tasks = [
            _fetch_adzuna_async(client, role, mkt),
            _fetch_adzuna_async(client, role_alt, mkt) if role_alt and role_alt.lower() != role.lower() else asyncio.sleep(0),
            _fetch_reed_async(client, role, mkt),
            _fetch_jsearch_async(client, role, mkt),
            _mock_jobs_for_market(mkt, profile),
        ]
        if mkt == "US":
            gather_tasks += [
                _fetch_usajobs_async(client, role),
                _fetch_isaca_rss_async(client, role),
                _fetch_indeed_rss_async(client, role, location or ""),
                _fetch_linkedin_rss_async(client, role, location or ""),
            ]
        if mkt == "IN":
            gather_tasks += [
                _fetch_naukri_rss_async(client, role),
            ]
        if is_research:
            # Phase 8D: Add academic/research-specific sources
            gather_tasks += [
                _fetch_nature_rss_async(client),
                _fetch_science_careers_rss_async(client, role),
            ]
        sources = await asyncio.gather(*gather_tasks, return_exceptions=True)

    all_jobs: List[Dict] = []
    sources_used: List[str] = []

    for result in sources:
        if isinstance(result, Exception):
            logger.debug("Source failed: %s", result)
            continue
        if isinstance(result, list) and result:
            all_jobs.extend(result)
            src = result[0].get("source", "Unknown")
            if src not in sources_used:
                sources_used.append(src)

    # Deduplicate by (title, company)
    seen: set = set()
    unique_jobs: List[Dict] = []
    for job in all_jobs:
        key = (job.get("title", "").lower()[:40], job.get("company", "").lower()[:20])
        if key not in seen:
            seen.add(key)
            unique_jobs.append(job)

    # Apply filters
    filtered = _apply_filters(unique_jobs, remote=remote, location=location, salary_min=salary_min)

    # Hire-probability scoring (Phase 8C)
    scored = _compute_hire_probability(filtered, profile, mkt)
    scored.sort(key=lambda j: j["hire_probability"], reverse=True)

    # Flag top 10 as PRIORITY
    for i, job in enumerate(scored[:10]):
        job["priority"] = True
    for job in scored[10:]:
        job["priority"] = False

    # Market intelligence from JD corpus
    mi = _analyze_market_intelligence(unique_jobs, mkt)

    return {
        "jobs": scored[:max_results],
        "market": mkt,
        "total_found": len(unique_jobs),
        "filtered_count": len(filtered),
        "sources_used": sources_used or ["Mock"],
        "market_intelligence": mi,
    }


def recommend_jobs(
    profile: Dict[str, Any],
    market: str = "US",
    max_results: int = 10,
) -> List[Dict[str, Any]]:
    """Sync wrapper for backward compatibility with existing api_routes.py."""
    result = asyncio.run(recommend_jobs_async(profile, market, max_results))
    return result["jobs"]


def get_trending_roles(market: str = "US") -> List[Dict[str, Any]]:
    """Return hottest IT Audit / AI Governance roles per market."""
    if market.upper() == "IN":
        return [
            {"title": "AI Governance & Audit Lead",       "growth": "+48%", "avg_salary": "₹28L–₹45L",  "demand": "Critical"},
            {"title": "CISA-Certified IT Auditor",        "growth": "+32%", "avg_salary": "₹20L–₹32L",  "demand": "Critical"},
            {"title": "Cloud Security Auditor (Azure)",   "growth": "+55%", "avg_salary": "₹22L–₹40L",  "demand": "High"},
            {"title": "GRC Lead – Big4 Advisory",         "growth": "+28%", "avg_salary": "₹25L–₹42L",  "demand": "High"},
            {"title": "SOX ITGC Senior Auditor",          "growth": "+20%", "avg_salary": "₹18L–₹28L",  "demand": "High"},
            {"title": "IT Risk & Compliance Manager",     "growth": "+35%", "avg_salary": "₹22L–₹38L",  "demand": "Medium"},
            {"title": "AI Ethics & Responsible AI Lead",  "growth": "+62%", "avg_salary": "₹30L–₹55L",  "demand": "Critical"},
        ]
    # US market
    return [
        {"title": "AI Audit Manager",                     "growth": "+42%", "avg_salary": "$145,000",  "demand": "Critical"},
        {"title": "AI Governance Analyst",                "growth": "+67%", "avg_salary": "$125,000",  "demand": "Critical"},
        {"title": "Cloud Security Auditor",               "growth": "+55%", "avg_salary": "$140,000",  "demand": "High"},
        {"title": "Chief Audit Executive (CAE)",          "growth": "+18%", "avg_salary": "$195,000",  "demand": "High"},
        {"title": "SOX / IT Audit Director",              "growth": "+22%", "avg_salary": "$165,000",  "demand": "High"},
        {"title": "IT Risk & Compliance Manager",         "growth": "+31%", "avg_salary": "$130,000",  "demand": "Medium"},
        {"title": "Model Risk Governance Lead",           "growth": "+48%", "avg_salary": "$152,000",  "demand": "Critical"},
    ]


# ── API fetchers ───────────────────────────────────────────────────────────

async def _fetch_adzuna_async(
    client: httpx.AsyncClient, role: str, market: str
) -> List[Dict]:
    if not (ADZUNA_APP_ID and ADZUNA_APP_KEY):
        return []
    url    = _ADZUNA_US if market == "US" else _ADZUNA_IN
    params = {
        "app_id":           ADZUNA_APP_ID,
        "app_key":          ADZUNA_APP_KEY,
        "results_per_page": 10,
        "what":             role,
        "sort_by":          "date",
        "max_days_old":     14,
    }
    try:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        return [_normalise_adzuna(j, market) for j in resp.json().get("results", [])]
    except Exception as exc:
        logger.debug("Adzuna %s failed: %s", market, exc)
        return []


async def _fetch_reed_async(
    client: httpx.AsyncClient, role: str, market: str
) -> List[Dict]:
    """Reed.co.uk — strong India/UK market coverage."""
    if not REED_API_KEY:
        return []
    # Reed uses Basic Auth with API key as username
    params = {"keywords": role, "resultsToTake": 10}
    if market == "IN":
        params["locationName"] = "India"
    try:
        resp = await client.get(
            _REED_BASE,
            params=params,
            auth=(REED_API_KEY, ""),
        )
        resp.raise_for_status()
        return [_normalise_reed(j) for j in resp.json().get("results", [])]
    except Exception as exc:
        logger.debug("Reed %s failed: %s", market, exc)
        return []


async def _fetch_jsearch_async(
    client: httpx.AsyncClient, role: str, market: str
) -> List[Dict]:
    """JSearch (RapidAPI) — backup source, 500 req/month free."""
    if not JSEARCH_API_KEY:
        return []
    query = f"{role} {'India' if market == 'IN' else 'USA'}"
    try:
        resp = await client.get(
            _JSEARCH,
            params={"query": query, "page": "1", "num_pages": "1"},
            headers={
                "X-RapidAPI-Key": JSEARCH_API_KEY,
                "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
            },
        )
        resp.raise_for_status()
        return [_normalise_jsearch(j) for j in resp.json().get("data", [])]
    except Exception as exc:
        logger.debug("JSearch %s failed: %s", market, exc)
        return []


async def _fetch_usajobs_async(
    client: httpx.AsyncClient, role: str
) -> List[Dict]:
    """USAJobs.gov — federal IT audit / AI governance roles (free, no API key)."""
    try:
        resp = await client.get(
            _USAJOBS,
            params={
                "Keyword":          role,
                "ResultsPerPage":   10,
                "Fields":           "Min",
            },
            headers={
                "Host":          "data.usajobs.gov",
                "User-Agent":    "cert-navigator/1.0 (career-tool)",
                "Authorization-Key": os.getenv("USAJOBS_API_KEY", ""),
            },
        )
        resp.raise_for_status()
        items = resp.json().get("SearchResult", {}).get("SearchResultItems", [])
        return [_normalise_usajobs(item) for item in items if item]
    except Exception as exc:
        logger.debug("USAJobs failed: %s", exc)
        return []


async def _fetch_isaca_rss_async(
    client: httpx.AsyncClient, role: str
) -> List[Dict]:
    """ISACA job board RSS — cert-specific roles (no API key needed)."""
    try:
        resp = await client.get(_ISACA_RSS, timeout=5.0)
        resp.raise_for_status()
        return _parse_rss(resp.text, source="ISACA", market="US", role_filter=role)
    except Exception as exc:
        logger.debug("ISACA RSS failed: %s", exc)
        return []


async def _fetch_indeed_rss_async(
    client: httpx.AsyncClient, role: str, location: str = ""
) -> List[Dict]:
    """Indeed RSS feed — broad market signal (no API key)."""
    try:
        url = _INDEED_RSS.format(
            query=role.replace(" ", "+"),
            location=location.replace(" ", "+") or "Remote",
        )
        resp = await client.get(url, timeout=5.0,
                                headers={"User-Agent": "Mozilla/5.0 cert-navigator"})
        resp.raise_for_status()
        return _parse_rss(resp.text, source="Indeed", market="US", role_filter=role)
    except Exception as exc:
        logger.debug("Indeed RSS failed: %s", exc)
        return []


async def _fetch_nature_rss_async(client: httpx.AsyncClient) -> List[Dict]:
    """Nature Careers RSS — research/academic positions (no API key)."""
    try:
        resp = await client.get(_NATURE_RSS, timeout=5.0,
                                headers={"User-Agent": "Mozilla/5.0 cert-navigator"})
        resp.raise_for_status()
        return _parse_rss(resp.text, source="Nature Careers", market="US")
    except Exception as exc:
        logger.debug("Nature Careers RSS failed: %s", exc)
        return []


async def _fetch_science_careers_rss_async(
    client: httpx.AsyncClient, role: str
) -> List[Dict]:
    """Science Careers RSS (AAAS) — research/lab positions (no API key)."""
    try:
        url = _SCIENCE_RSS.format(query=role.replace(" ", "+"))
        resp = await client.get(url, timeout=5.0,
                                headers={"User-Agent": "Mozilla/5.0 cert-navigator"})
        resp.raise_for_status()
        return _parse_rss(resp.text, source="Science Careers", market="US")
    except Exception as exc:
        logger.debug("Science Careers RSS failed: %s", exc)
        return []


async def _fetch_linkedin_rss_async(
    client: httpx.AsyncClient, role: str, location: str = ""
) -> List[Dict]:
    """LinkedIn job RSS — most regions return HTML; silently returns empty list on failure."""
    try:
        url = _LINKEDIN_RSS.format(
            role=role.replace(" ", "%20"),
            loc=location.replace(" ", "%20") or "Remote",
        )
        resp = await client.get(url, timeout=5.0,
                                headers={"User-Agent": "Mozilla/5.0 cert-navigator"})
        resp.raise_for_status()
        return _parse_rss(resp.text, source="LinkedIn", market="US", role_filter=role)
    except Exception as exc:
        logger.debug("LinkedIn RSS failed: %s", exc)
        return []


async def _fetch_naukri_rss_async(
    client: httpx.AsyncClient, role: str
) -> List[Dict]:
    """Naukri job API — India market; silently returns empty list on failure."""
    try:
        url = _NAUKRI_API.format(role=role.replace(" ", "+"))
        resp = await client.get(
            url, timeout=5.0,
            headers={
                "User-Agent": "Mozilla/5.0 cert-navigator",
                "appid": "109",
                "systemid": "109",
            },
        )
        resp.raise_for_status()
        data = resp.json()
        jobs_raw = data.get("jobDetails") or data.get("jobs") or []
        result = []
        for j in jobs_raw[:10]:
            title = j.get("title") or j.get("jobTitle") or ""
            result.append({
                "id":             f"naukri-{abs(hash(title + j.get('jobId','')[:6])) % 100000}",
                "title":          title,
                "company":        j.get("companyName") or j.get("company") or "",
                "location":       j.get("placeholders", [{}])[0].get("label") if j.get("placeholders") else j.get("location") or "India",
                "salary_min":     None,
                "salary_max":     None,
                "description":    (j.get("jobDescription") or "")[:600],
                "url":            j.get("jdURL") or j.get("applyRedirectURL") or "",
                "posted":         j.get("createdDate") or datetime.utcnow().isoformat(),
                "source":         "Naukri",
                "market":         "IN",
                "remote":         "remote" in (title + " " + (j.get("jobDescription") or "")).lower(),
                "match_score":    0,
                "hire_probability": 0,
                "skills_matched": [],
                "tags":           [],
            })
        return result
    except Exception as exc:
        logger.debug("Naukri API failed: %s", exc)
        return []


async def _mock_jobs_for_market(market: str, profile: Optional[Dict] = None) -> List[Dict]:
    """
    Return domain-appropriate mock jobs for the user's profile.
    Classifies the profile domain and serves matching mock jobs.
    Falls back to IT audit mocks if domain has no dedicated set.
    """
    if profile:
        try:
            from src.backend.engine.domain_classifier import (
                classify as classify_domain,
                get_domain_mock_jobs,
            )
            domain = classify_domain(profile)
            domain_jobs = get_domain_mock_jobs(domain, market)
            if domain_jobs:
                return domain_jobs
        except Exception:
            pass  # fall through to IT audit defaults
    return _mock_us_jobs() if market == "US" else _mock_india_jobs()


# ── Normalisation ──────────────────────────────────────────────────────────

def _normalise_adzuna(raw: Dict, market: str = "US") -> Dict:
    return {
        "id":           f"az-{raw.get('id', '')}",
        "title":        raw.get("title", ""),
        "company":      raw.get("company", {}).get("display_name", ""),
        "location":     raw.get("location", {}).get("display_name", ""),
        "salary_min":   raw.get("salary_min"),
        "salary_max":   raw.get("salary_max"),
        "description":  (raw.get("description") or "")[:600],
        "url":          raw.get("redirect_url", ""),
        "posted":       raw.get("created", datetime.utcnow().isoformat()),
        "source":       "Adzuna",
        "market":       market,
        "match_score":  0,
        "skills_matched": [],
        "tags":         [],
    }


def _normalise_reed(raw: Dict) -> Dict:
    return {
        "id":           f"reed-{raw.get('jobId', '')}",
        "title":        raw.get("jobTitle", ""),
        "company":      raw.get("employerName", ""),
        "location":     raw.get("locationName", ""),
        "salary_min":   raw.get("minimumSalary"),
        "salary_max":   raw.get("maximumSalary"),
        "description":  (raw.get("jobDescription") or "")[:600],
        "url":          raw.get("jobUrl", ""),
        "posted":       raw.get("date", datetime.utcnow().isoformat()),
        "source":       "Reed",
        "market":       "IN",
        "match_score":  0,
        "skills_matched": [],
        "tags":         [],
    }


def _normalise_jsearch(raw: Dict) -> Dict:
    return {
        "id":           f"js-{raw.get('job_id', '')}",
        "title":        raw.get("job_title", ""),
        "company":      raw.get("employer_name", ""),
        "location":     f"{raw.get('job_city','')}, {raw.get('job_country','')}",
        "salary_min":   raw.get("job_min_salary"),
        "salary_max":   raw.get("job_max_salary"),
        "description":  (raw.get("job_description") or "")[:600],
        "url":          raw.get("job_apply_link", ""),
        "posted":       raw.get("job_posted_at_datetime_utc", datetime.utcnow().isoformat()),
        "source":       "JSearch",
        "market":       "US",
        "match_score":  0,
        "skills_matched": [],
        "tags":         [],
    }


def _normalise_usajobs(raw: Dict) -> Dict:
    pos = raw.get("MatchedObjectDescriptor", {})
    pay = pos.get("PositionRemuneration", [{}])[0] if pos.get("PositionRemuneration") else {}
    loc = ", ".join(l.get("LocationName", "") for l in pos.get("PositionLocation", [])[:2])
    return {
        "id":           f"usajobs-{pos.get('PositionID', '')}",
        "title":        pos.get("PositionTitle", ""),
        "company":      pos.get("OrganizationName", "US Federal Government"),
        "location":     loc or "Washington, DC",
        "salary_min":   _safe_int(pay.get("MinimumRange")),
        "salary_max":   _safe_int(pay.get("MaximumRange")),
        "description":  (pos.get("QualificationSummary") or "")[:600],
        "url":          pos.get("PositionURI", ""),
        "posted":       pos.get("PublicationStartDate", datetime.utcnow().isoformat()),
        "source":       "USAJobs",
        "market":       "US",
        "remote":       "remote" in (loc + " " + pos.get("PositionTitle", "")).lower(),
        "match_score":  0,
        "hire_probability": 0,
        "skills_matched": [],
        "tags":         [],
    }


def _parse_rss(xml_text: str, source: str, market: str, role_filter: str = "") -> List[Dict]:
    """Parse generic RSS feed into normalised job dicts."""
    jobs: List[Dict] = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []
    ns = {"dc": "http://purl.org/dc/elements/1.1/"}
    for item in root.findall(".//item")[:10]:
        title = (item.findtext("title") or "").strip()
        if role_filter and not any(
            w.lower() in title.lower() for w in role_filter.split()[:3]
        ):
            continue
        desc  = re.sub(r"<[^>]+>", "", item.findtext("description") or "")[:600]
        link  = item.findtext("link") or ""
        pubdate = item.findtext("pubDate") or datetime.utcnow().isoformat()
        company = item.findtext("dc:creator", namespaces=ns) or source
        jobs.append({
            "id":             f"{source.lower()}-{abs(hash(title + link)) % 100000}",
            "title":          title,
            "company":        company,
            "location":       "Remote" if "remote" in title.lower() else "Various",
            "salary_min":     None,
            "salary_max":     None,
            "description":    desc,
            "url":            link,
            "posted":         pubdate,
            "source":         source,
            "market":         market,
            "remote":         "remote" in (title + " " + desc).lower(),
            "match_score":    0,
            "hire_probability": 0,
            "skills_matched": [],
            "tags":           [],
        })
    return jobs


def _safe_int(val) -> Optional[int]:
    try:
        return int(float(val)) if val else None
    except (ValueError, TypeError):
        return None


# ── Phase 8C: Filter + Hire-Probability Scoring ────────────────────────────

def _apply_filters(
    jobs: List[Dict],
    remote: Optional[bool],
    location: Optional[str],
    salary_min: Optional[int],
) -> List[Dict]:
    """Apply remote/location/salary_min filters to job list."""
    result = jobs
    if remote is True:
        result = [j for j in result if
                  j.get("remote") or "remote" in (j.get("location","") + j.get("title","")).lower()]
    elif remote is False:
        result = [j for j in result if
                  not (j.get("remote") or "remote" in j.get("location","").lower())]
    if location:
        loc_lower = location.lower()
        result = [j for j in result if loc_lower in j.get("location","").lower()
                  or "remote" in j.get("location","").lower()]
    if salary_min is not None:
        result = [j for j in result if
                  j.get("salary_min") is None or j["salary_min"] >= salary_min]
    return result


def _compute_hire_probability(
    jobs: List[Dict], profile: Dict[str, Any], market: str = "US"
) -> List[Dict]:
    """
    Phase 8C: Hire-Probability Score (0-100) per job.

    Weights:
      Cert match      40% — user holds cert mentioned in JD
      Skill overlap   30% — matched_skills / required_skills
      Seniority fit   20% — user experience_years vs JD seniority signals
      Market velocity 10% — how fast this role's skill-set is growing
    """
    user_skills   = {s.lower() for s in profile.get("skills", [])}
    user_certs    = {
        (c.get("name", c) if isinstance(c, dict) else str(c)).upper()
        for c in profile.get("certifications", [])
    }
    exp_years     = profile.get("experience_years") or 0
    mkt_key       = market.lower()

    for job in jobs:
        blob = (
            job.get("title","") + " " + job.get("description","") + " "
            + " ".join(job.get("tags",[]))
        ).lower()

        # ── Cert match (40 pts) ────────────────────────────────────────────
        cert_hits = sum(1 for c in user_certs if c.lower() in blob)
        cert_score = min(40, cert_hits * 15)

        # ── Skill overlap (30 pts) ─────────────────────────────────────────
        matched = [s for s in user_skills if s.lower() in blob]
        # Estimate required skills from blob length proxy (10 words ≈ 1 requirement)
        required_est = max(len(blob.split()) // 10, 1)
        overlap_ratio = min(len(matched) / required_est, 1.0)
        skill_score = int(30 * overlap_ratio)

        # ── Seniority fit (20 pts) ─────────────────────────────────────────
        jd_level = 0
        for signals, level in _SENIORITY_PATTERNS:
            if any(sig in blob for sig in signals):
                jd_level = level
                break
        # Map experience_years → seniority tier (0-15 scale)
        user_level = (
            15 if exp_years >= 12 else
            12 if exp_years >= 8 else
            9  if exp_years >= 5 else
            6  if exp_years >= 3 else
            4  if exp_years >= 1 else
            1
        )
        level_diff  = abs(user_level - jd_level)
        sen_score   = max(0, 20 - level_diff * 3)

        # ── Market velocity (10 pts) ───────────────────────────────────────
        velocity = 0
        for skill_key, data in _SKILL_SIGNALS.items():
            if skill_key in blob and data.get("trajectory") == "rising":
                velocity = min(velocity + data.get(mkt_key, 0) // 10, 10)
        velocity_score = min(velocity, 10)

        hp = cert_score + skill_score + sen_score + velocity_score
        job["hire_probability"] = min(hp, 100)
        job["match_score"]      = job["hire_probability"]   # backward compat
        job["skills_matched"]   = list(set(matched))
        job["hire_breakdown"]   = {
            "cert_match":      cert_score,
            "skill_overlap":   skill_score,
            "seniority_fit":   sen_score,
            "market_velocity": velocity_score,
        }

    return jobs


# ── (legacy) Scoring ────────────────────────────────────────────────────────
# Kept for backward compat; new code uses _compute_hire_probability above.

def _rank_and_score(
    jobs: List[Dict], profile: Dict[str, Any], market: str = "US"
) -> List[Dict]:
    """
    Score each job against the user profile.
    Weights are market-adjusted: India weights certifications higher (Big4 culture).
    """
    user_skills   = {s.lower() for s in profile.get("skills", [])}
    user_location = (profile.get("location") or "").lower()
    user_certs    = {
        (c.get("name", c) if isinstance(c, dict) else str(c)).upper()
        for c in profile.get("certifications", [])
    }
    target_words  = set((profile.get("target_role") or "").lower().split())

    # Market-specific location anchors
    loc_anchors = (
        ["bangalore", "hyderabad", "mumbai", "pune", "chennai", "delhi", "remote", "india"]
        if market == "IN"
        else ["los angeles", "torrance", "remote", "new york", "chicago"]
    )

    for job in jobs:
        score   = 0
        matched: List[str] = []
        blob    = (
            job["title"] + " " + job.get("description","") + " "
            + " ".join(job.get("tags", []))
        ).lower()

        # Skill match (+8 each, cap at 40 from skills)
        skill_score = 0
        for skill in user_skills:
            if skill.lower() in blob:
                matched.append(skill.title())
                skill_score = min(skill_score + 8, 40)
        score += skill_score

        # Cert match (+15 each, higher weight for India — cert culture)
        cert_weight = 18 if market == "IN" else 15
        for cert in user_certs:
            if cert.lower() in blob:
                score += cert_weight

        # Title relevance (+20)
        if target_words and any(w in job["title"].lower() for w in target_words if len(w) > 3):
            score += 20

        # Location match (+5)
        job_loc = job.get("location", "").lower()
        if any(a in job_loc for a in loc_anchors) or any(a in user_location for a in loc_anchors[:2]):
            score += 5

        # AI/governance premium (+10 for 2026 market)
        if any(kw in blob for kw in ["ai audit", "ai governance", "aigp", "nist ai rmf"]):
            score += 10

        job["match_score"]    = min(score, 100)
        job["skills_matched"] = list(set(matched))

    return sorted(jobs, key=lambda j: j["match_score"], reverse=True)


# ── Market Intelligence ────────────────────────────────────────────────────

def _analyze_market_intelligence(
    jobs: List[Dict], market: str
) -> Dict[str, Any]:
    """
    Analyze the JD corpus to surface:
    - Trending skills (most frequently demanded)
    - Skill trajectory (rising/stable/declining)
    - Salary momentum
    - Top hiring companies
    """
    corpus = " ".join(
        (j.get("description","") + " " + j.get("title","") + " " + " ".join(j.get("tags",[])))
        for j in jobs
    ).lower()

    trending, declining = [], []
    for skill, data in _SKILL_SIGNALS.items():
        freq   = corpus.count(skill)
        change = data.get(market.lower(), data.get("us", 0))
        entry  = {"skill": skill.title(), "demand_change_pct": change, "frequency": freq}
        if change > 0 and freq > 0:
            trending.append(entry)
        elif change < 0:
            declining.append(entry)

    trending.sort(key=lambda x: x["demand_change_pct"], reverse=True)

    # Salary momentum
    salaries = [j for j in jobs if j.get("salary_min")]
    avg_min  = int(sum(j["salary_min"] for j in salaries) / len(salaries)) if salaries else 0
    avg_max  = int(sum(j.get("salary_max") or j["salary_min"] for j in salaries) / len(salaries)) if salaries else 0

    # Top hiring companies
    from collections import Counter
    companies = Counter(j.get("company","") for j in jobs if j.get("company"))
    top_companies = [{"company": c, "count": n} for c, n in companies.most_common(5)]

    return {
        "trending_skills": trending[:6],
        "declining_skills": declining[:4],
        "avg_salary_range": {"min": avg_min, "max": avg_max, "currency": "USD" if market == "US" else "INR"},
        "top_hiring_companies": top_companies,
        "market": market,
        "snapshot_date": datetime.utcnow().strftime("%Y-%m-%d"),
        "insight": _market_insight(market, trending),
    }


def _market_insight(market: str, trending: List[Dict]) -> str:
    top = trending[0]["skill"] if trending else "AI Governance"
    if market == "IN":
        return (
            f"India IT Audit market is accelerating — {top} skills command a "
            "premium across Big4 and BFSI hiring. CISA remains the #1 required cert. "
            "Cloud audit roles (Azure, AWS) up 55% YoY in Bangalore and Hyderabad."
        )
    return (
        f"US market signal: {top} is the top differentiator for 2026. "
        "AIGP certification now commands a $25K-$35K salary premium over CISA-only. "
        "Remote roles represent 62% of new IT Audit postings."
    )


# ── Curated mock datasets ──────────────────────────────────────────────────

def _mock_us_jobs() -> List[Dict]:
    ts = datetime.utcnow().isoformat()
    base = {"posted": ts, "source": "Mock", "market": "US", "match_score": 0, "skills_matched": []}
    return [
        {**base, "id":"us-001","title":"IT Audit Manager – AI & Emerging Tech",
         "company":"Deloitte","location":"Los Angeles, CA (Hybrid)",
         "salary_min":130_000,"salary_max":160_000,
         "description":"Lead IT audit engagements focused on AI governance, ITGC, SOX. CISA required; AIGP preferred. Manage 4-6 auditors, Azure/AWS GRC.",
         "tags":["CISA","AIGP","SOX","AI Auditing","ITGC","Cloud","GRC"],
         "url":"https://apply.deloitte.com/careers/SearchJobs/IT%20Audit?libId=lpkl4asd0100hpgs02l2mh0i6&lang=en_US"},
        {**base,"id":"us-002","title":"Senior AI Governance & Ethics Auditor",
         "company":"KPMG Advisory","location":"Remote – US",
         "salary_min":120_000,"salary_max":148_000,
         "description":"AI model governance, bias detection, EU AI Act, NIST AI RMF, ISO 42001. AIGP strongly preferred. Build AI ethics audit methodology.",
         "tags":["AIGP","AI Auditing","NIST AI RMF","EU AI Act","ISO 42001"],
         "url":"https://jobs.kpmg.us/search/?keyword=AI+Governance+Ethics+Audit"},
        {**base,"id":"us-003","title":"SOX ITGC Audit Lead",
         "company":"Fidelity Investments","location":"Los Angeles, CA",
         "salary_min":115_000,"salary_max":138_000,
         "description":"Own SOX ITGC and ITAC audit program. Coordinate with external auditors. Access management, change management, CISA required.",
         "tags":["SOX","ITGC","ITAC","Risk Management","CISA"],
         "url":"https://jobs.fidelity.com/job-search-results/?keyword=IT+Audit+SOX"},
        {**base,"id":"us-004","title":"Cloud Security Audit Manager",
         "company":"Microsoft","location":"Remote – US",
         "salary_min":145_000,"salary_max":178_000,
         "description":"Lead cloud security audits across Azure, AWS, GCP. CCSP or CISM required. Zero Trust, CSPM tooling. Security by design.",
         "tags":["CCSP","CISM","Cloud","Azure","Zero Trust","Security"],
         "url":"https://careers.microsoft.com/us/en/search-results?keywords=Cloud+Security+Audit"},
        {**base,"id":"us-005","title":"Chief Audit Executive – Technology & AI",
         "company":"Banc of California","location":"Torrance, CA",
         "salary_min":185_000,"salary_max":220_000,
         "description":"Lead enterprise audit with AI audit mandate. CIA or CISA required. 12+ years. Board and audit committee reporting. Team of 20+.",
         "tags":["Leadership","CISA","CIA","AI Auditing","CAE","Executive"],
         "url":"https://www.linkedin.com/jobs/search/?keywords=Chief+Audit+Executive+Technology+AI&location=Los+Angeles%2C+CA"},
        {**base,"id":"us-006","title":"IT Risk & Compliance Manager",
         "company":"JPMorgan Chase","location":"Los Angeles, CA (Hybrid)",
         "salary_min":125_000,"salary_max":158_000,
         "description":"IT risk assessment, RCSA, OCC regulatory exams. CISA or CRISC required. GRC platforms (ServiceNow, AuditBoard, Vanta).",
         "tags":["CRISC","GRC","Risk Management","ServiceNow","Compliance"],
         "url":"https://jpmc.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1001/requisitions?keyword=IT+Risk+Compliance"},
        {**base,"id":"us-007","title":"AI Ethics & Model Risk Assurance Lead",
         "company":"PwC Advisory","location":"Remote – US",
         "salary_min":132_000,"salary_max":162_000,
         "description":"Build AI assurance practice. Responsible AI programs, model risk governance, AI regulatory compliance. AIGP differentiator. C-suite advisory.",
         "tags":["AIGP","AI Ethics","Model Risk","Consulting","Leadership"],
         "url":"https://jobs.us.pwc.com/en-us/search-jobs/AI+Ethics+Model+Risk+Audit"},
        {**base,"id":"us-008","title":"Senior IT Internal Auditor – AI Systems",
         "company":"Kaiser Permanente","location":"Torrance, CA (On-site)",
         "salary_min":105_000,"salary_max":128_000,
         "description":"Audit AI-powered clinical decision support systems. HIPAA compliance, model bias, explainability. CISA preferred. Healthcare IT audit.",
         "tags":["CISA","AI Auditing","HIPAA","Healthcare","Compliance"],
         "url":"https://jobs.kp.org/search/?q=IT+Audit+AI&keywords=IT+Internal+Auditor"},
        {**base,"id":"us-009","title":"GRC Platform Lead – AI Audit",
         "company":"ServiceNow","location":"Remote – US",
         "salary_min":135_000,"salary_max":165_000,
         "description":"Lead GRC platform implementations with AI audit workflows. ServiceNow IRM/GRC expertise required. CISA or CRISC preferred.",
         "tags":["ServiceNow","GRC","CISA","CRISC","Implementation"],
         "url":"https://careers.servicenow.com/jobs/?keyword=GRC+IT+Audit+CISA"},
        {**base,"id":"us-010","title":"Director of IT Audit – Digital Transformation",
         "company":"Los Angeles County","location":"Los Angeles, CA",
         "salary_min":155_000,"salary_max":185_000,
         "description":"Direct IT audit for largest US county government. AI/ML, cloud migration, ERP audits. CISA required; CIA preferred.",
         "tags":["CISA","CIA","Leadership","Public Sector","Cloud","ERP"],
         "url":"https://www.governmentjobs.com/careers/lacounty?keyword=IT+Audit+Director"},
    ]


def _mock_india_jobs() -> List[Dict]:
    ts = datetime.utcnow().isoformat()
    base = {"posted": ts, "source": "Mock", "market": "IN", "match_score": 0, "skills_matched": []}
    return [
        {**base,"id":"in-001","title":"IT Audit Manager – AI & Cloud Governance",
         "company":"Wipro","location":"Bangalore, Karnataka",
         "salary_min":2_200_000,"salary_max":3_500_000,
         "description":"Lead IT audit for AI and cloud platforms. CISA required; AIGP preferred. Manage team of 5 auditors. Azure, AWS governance. SOX controls for US clients.",
         "tags":["CISA","AIGP","Cloud","SOX","AI Auditing","GRC"],
         "url":"https://careers.wipro.com/careers-home/jobs?keyword=IT+Audit+AI+Cloud"},
        {**base,"id":"in-002","title":"Senior IS Auditor – GRC & Risk",
         "company":"Tata Consultancy Services","location":"Hyderabad, Telangana",
         "salary_min":1_800_000,"salary_max":2_800_000,
         "description":"ISACA certified IT auditor for BFSI clients. CISA or CRISC required. IT risk assessment, COBIT, ISO 27001 controls. Regulatory compliance for RBI/SEBI.",
         "tags":["CISA","CRISC","GRC","Risk Management","ISO 27001","COBIT"],
         "url":"https://www.tcs.com/careers/global/apply?keyword=IS+Auditor+GRC"},
        {**base,"id":"in-003","title":"AI Governance & Ethics Audit Lead",
         "company":"EY India","location":"Mumbai, Maharashtra",
         "salary_min":2_800_000,"salary_max":4_500_000,
         "description":"Build AI governance audit methodology for financial services. NIST AI RMF, ISO 42001, EU AI Act compliance advisory. AIGP certification a strong differentiator.",
         "tags":["AIGP","AI Governance","NIST AI RMF","EU AI Act","ISO 42001","Consulting"],
         "url":"https://eyglobal.yello.co/jobs?country=India&keyword=AI+Governance+Audit"},
        {**base,"id":"in-004","title":"Cloud Security Audit Specialist",
         "company":"Infosys","location":"Pune, Maharashtra",
         "salary_min":2_000_000,"salary_max":3_200_000,
         "description":"Audit Azure, AWS, and GCP deployments. CCSP or CISM preferred. Cloud ITGC, Zero Trust, CSPM. Work with global delivery centers.",
         "tags":["CCSP","CISM","Cloud","Azure","AWS","Zero Trust"],
         "url":"https://career.infosys.com/jobdesc.html?jobid=INFSYS-EXTERNAL-CLOUD-AUDIT"},
        {**base,"id":"in-005","title":"AI Risk & Controls Manager",
         "company":"HDFC Bank","location":"Mumbai, Maharashtra",
         "salary_min":2_500_000,"salary_max":4_000_000,
         "description":"Establish AI model risk governance framework. Bias testing, model validation, RBI AI guidelines compliance. CISA or AIGP preferred. 8+ years audit experience.",
         "tags":["AI Auditing","Model Risk","CISA","AIGP","Banking","Compliance"],
         "url":"https://www.linkedin.com/jobs/search/?keywords=AI+Risk+Controls+Manager&location=Mumbai%2C+Maharashtra"},
        {**base,"id":"in-006","title":"SOX ITGC Audit Lead – US Clients",
         "company":"Amazon India","location":"Hyderabad, Telangana",
         "salary_min":2_000_000,"salary_max":3_000_000,
         "description":"Own SOX ITGC program supporting US public company filings. CISA required. IT General Controls, change management, access controls, ITAC testing.",
         "tags":["SOX","ITGC","CISA","IT Controls","Compliance","US Standards"],
         "url":"https://amazon.jobs/en/search?base_query=IT+Audit+SOX+ITGC&loc_query=Hyderabad%2C+India"},
        {**base,"id":"in-007","title":"IT Risk & Compliance Manager – FinTech",
         "company":"Cognizant","location":"Chennai, Tamil Nadu",
         "salary_min":1_800_000,"salary_max":2_800_000,
         "description":"IT risk management for FinTech clients. CISA or CRISC. RBI IT framework, PCI DSS, GDPR compliance. GRC platforms (ServiceNow, MetricStream).",
         "tags":["CRISC","GRC","PCI DSS","GDPR","ServiceNow","FinTech"],
         "url":"https://careers.cognizant.com/india/en/search-results?keywords=IT+Risk+Compliance+CISA"},
        {**base,"id":"in-008","title":"Cybersecurity Audit Specialist",
         "company":"ICICI Bank","location":"Mumbai, Maharashtra",
         "salary_min":2_200_000,"salary_max":3_500_000,
         "description":"Information security audits. ISO 27001, NIST CSF, RBI cybersecurity circular compliance. CISA/CISSP preferred. Vulnerability assessment, incident response.",
         "tags":["CISA","CISSP","ISO 27001","Cybersecurity","NIST","Banking"],
         "url":"https://www.linkedin.com/jobs/search/?keywords=Cybersecurity+Audit+ICICI+Bank&location=Mumbai"},
        {**base,"id":"in-009","title":"Senior IT Audit Manager – Digital Banking",
         "company":"Deloitte India","location":"Bangalore, Karnataka",
         "salary_min":3_000_000,"salary_max":5_000_000,
         "description":"Lead digital banking audit practice. AI/ML risk, open banking APIs, digital payments. CISA required; AIGP and CCSP preferred. Manage 8-10 person team.",
         "tags":["CISA","AIGP","CCSP","Digital Banking","AI Auditing","Leadership"],
         "url":"https://apply.deloitte.com/careers/SearchJobs/IT%20Audit?libId=lpkl4asd0100hpgs02l2mh0i6&lang=en_US"},
        {**base,"id":"in-010","title":"AI Risk & Data Governance Lead",
         "company":"Google India","location":"Hyderabad, Telangana",
         "salary_min":3_500_000,"salary_max":6_000_000,
         "description":"Build AI governance and data risk frameworks. Bias mitigation, explainability, EU AI Act compliance. Experience with responsible AI toolkits. Python preferred.",
         "tags":["AI Governance","Data Governance","EU AI Act","Python","Responsible AI"],
         "url":"https://careers.google.com/jobs/results/?q=AI+Risk+Governance&location=Hyderabad%2C+India"},
    ]
