"""
Async resume parser — handles JSON and PDF formats.

Produces a normalised profile dict compatible with both the existing
certifications_catalog engine and the new pgvector skill matching pipeline.

⚠️ CAPACITY FLAG: pdfplumber is CPU-bound (~1-3s per PDF page).
For > 10 concurrent PDF uploads: Celery worker is required.
Trigger: Monitor /users/me/resume endpoint p95 latency — if > 2s, move to
Celery task `tasks.parse_resume_async`.
"""
import asyncio
import io
import json
import logging
import re
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# ── Skill taxonomy for extraction ─────────────────────────────────────────
# Expanded from the existing parser, aligned with certlab-saas-v2.html domains
SKILL_KEYWORDS = {
    # AI & Governance
    "ai governance", "nist ai rmf", "eu ai act", "iso 42001", "ai audit",
    "ai risk management", "model risk", "responsible ai", "ai ethics",
    "fairness metrics", "disparate impact", "ai controls",
    # Cybersecurity
    "cisa", "cissp", "soc 2", "iso 27001", "nist 800-53", "zero trust",
    "penetration testing", "vulnerability assessment", "siem", "soc operations",
    "incident response", "threat modeling", "dlp", "iam", "pam",
    # Audit & Compliance
    "sox auditing", "it audit", "internal audit", "risk assessment",
    "control testing", "gdpr", "hipaa", "pci dss", "itgc",
    "data governance", "audit methodology", "coso", "cobit",
    # Cloud & Architecture
    "aws", "azure", "gcp", "cloud security", "ccsp", "cloud architecture",
    "kubernetes", "docker", "terraform", "devops", "devsecops",
    # Data & Analytics
    "python", "sql", "data analysis", "power bi", "tableau", "excel",
    "machine learning", "nlp", "data science", "etl", "big data",
    # Leadership & Strategy
    "risk management", "project management", "stakeholder management",
    "strategic planning", "change management", "team leadership",
}

CERT_PATTERNS = [
    r"\bCISA\b", r"\bCISSP\b", r"\bCISM\b", r"\bCRISC\b", r"\bCGEIT\b",
    r"\bCCSP\b", r"\bAIGP\b", r"\bAAISM\b", r"\bCIASP\b", r"\bCIA\b",
    r"\bCPA\b", r"\bCFE\b", r"\bCDPSE\b", r"\bOSCP\b", r"\bSecurity\+",
    r"\bAWS\s+Certified", r"\bGoogle\s+Cloud\s+Professional",
    r"\bAzure\s+(?:Administrator|Architect|Security)",
]

ROLE_PATTERNS = {
    "ciso": "CISO",
    "chief information security": "CISO",
    "vp.*security": "VP of Security",
    "director.*audit": "Director of Audit",
    "cae": "Chief Audit Executive",
    "chief audit": "Chief Audit Executive",
    "it audit manager": "IT Audit Manager",
    "senior.*audit": "Senior Auditor",
    "audit manager": "Audit Manager",
    "risk manager": "Risk Manager",
    "compliance manager": "Compliance Manager",
    "security analyst": "Security Analyst",
    "security engineer": "Security Engineer",
    "cloud architect": "Cloud Architect",
    "ai.*engineer": "AI Engineer",
    "data scientist": "Data Scientist",
}


async def parse_resume_bytes(
    content: bytes,
    content_type: str,
    filename: str = "",
) -> Dict[str, Any]:
    """
    Dispatch to the appropriate parser based on content type.
    Runs in executor to stay async-safe.
    """
    ct = content_type.lower()
    fname = filename.lower()

    if "json" in ct or fname.endswith(".json"):
        return await _parse_json(content)
    elif "pdf" in ct or fname.endswith(".pdf"):
        return await _parse_pdf(content)
    else:
        # Fallback: try JSON, then PDF
        try:
            return await _parse_json(content)
        except Exception:
            return await _parse_pdf(content)


async def _parse_json(content: bytes) -> Dict[str, Any]:
    """Parse a structured JSON resume."""
    try:
        raw = json.loads(content.decode("utf-8"))
    except Exception as exc:
        raise ValueError(f"Invalid JSON: {exc}") from exc
    return _normalise(raw)


async def _parse_pdf(content: bytes) -> Dict[str, Any]:
    """
    Extract text from PDF using pdfplumber, then run NLP extraction.
    Offloaded to executor thread — pdfplumber is synchronous and CPU-bound.
    """
    loop = asyncio.get_event_loop()
    text = await loop.run_in_executor(None, _extract_pdf_text, content)
    return _extract_from_text(text)


def _extract_pdf_text(content: bytes) -> str:
    """Synchronous PDF text extraction (runs in executor)."""
    try:
        import pdfplumber  # type: ignore

        with pdfplumber.open(io.BytesIO(content)) as pdf:
            pages = [page.extract_text() or "" for page in pdf.pages]
        return "\n".join(pages)
    except ImportError:
        logger.warning("pdfplumber not installed — PDF parsing unavailable")
        return ""
    except Exception as exc:
        logger.error("PDF extraction error: %s", exc)
        return ""


def _extract_from_text(text: str) -> Dict[str, Any]:
    """
    NLP-lite extraction from raw resume text.
    Identifies: name, email, phone, current_role, skills, certifications, experience.
    """
    lower = text.lower()

    # Email
    email_match = re.search(r"[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}", text)
    email = email_match.group(0) if email_match else None

    # Phone
    phone_match = re.search(
        r"(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", text
    )
    phone = phone_match.group(0) if phone_match else None

    # Current role (first role-like phrase near the top)
    current_role = _extract_role(text[:500])

    # Skills
    skills = _extract_skills(lower)

    # Certifications
    certifications = _extract_certifications(text)

    # Years of experience
    exp_match = re.search(r"(\d+)\+?\s*years?\s+(?:of\s+)?experience", lower)
    experience_years = int(exp_match.group(1)) if exp_match else None

    # Location (look for city, state patterns)
    loc_match = re.search(
        r"([A-Z][a-zA-Z\s]+),\s*([A-Z]{2})\b", text[:300]
    )
    location = loc_match.group(0) if loc_match else None

    return _normalise({
        "email": email,
        "phone": phone,
        "current_role": current_role,
        "skills": skills,
        "certifications": certifications,
        "experience_years": experience_years,
        "location": location,
    })


def _extract_role(text_segment: str) -> str:
    """Extract the most prominent job title from a text segment."""
    lower = text_segment.lower()
    for pattern, role_name in ROLE_PATTERNS.items():
        if re.search(pattern, lower):
            return role_name
    return "Professional"


def _extract_skills(lower_text: str) -> List[str]:
    """Match known skill keywords in resume text."""
    found = []
    for skill in SKILL_KEYWORDS:
        if skill in lower_text:
            found.append(skill.title())
    return sorted(set(found))


def _extract_certifications(text: str) -> List[Dict[str, str]]:
    """Extract certification acronyms using regex patterns."""
    found = []
    for pattern in CERT_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            cert_name = match.strip()
            if cert_name not in [c["name"] for c in found]:
                found.append({"name": cert_name, "status": "active"})
    return found


def _normalise(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalise any resume dict to the canonical schema.
    Handles both structured JSON resumes and NLP-extracted dicts.
    """
    def _get(*keys, default=None):
        for k in keys:
            v = raw.get(k)
            if v is not None:
                return v
        return default

    skills_raw = _get("skills", "skill_set", "competencies", default=[])
    if isinstance(skills_raw, str):
        skills = [s.strip() for s in skills_raw.split(",") if s.strip()]
    elif isinstance(skills_raw, list):
        # Each item can be str or {"name": "...", "level": "..."}
        skills = []
        for s in skills_raw:
            if isinstance(s, str):
                skills.append(s.strip())
            elif isinstance(s, dict):
                skills.append(str(s.get("name", s.get("skill", ""))))
    else:
        skills = []

    certs_raw = _get("certifications", "certs", "credentials", default=[])
    if isinstance(certs_raw, list):
        certs = []
        for c in certs_raw:
            if isinstance(c, str):
                certs.append({"name": c, "status": "active"})
            elif isinstance(c, dict):
                certs.append({
                    "name": c.get("name", c.get("cert", "")),
                    "status": c.get("status", "active"),
                    "year": c.get("year"),
                })
    else:
        certs = []

    edu_raw = _get("education", default=[])
    if isinstance(edu_raw, list):
        education = edu_raw
    elif isinstance(edu_raw, dict):
        education = [edu_raw]
    else:
        education = []

    return {
        "name": _get("name", "full_name", default=""),
        "email": _get("email", default=""),
        "phone": _get("phone", "phone_number", default=""),
        "current_role": _get("current_role", "title", "position", "job_title", default=""),
        "target_role": _get("target_role", "desired_role", default=""),
        "experience_years": _get("experience_years", "years_experience", "years", default=0),
        "location": _get("location", "city", default=""),
        "summary": _get("summary", "bio", "about", default=""),
        "skills": [s for s in skills if s],
        "certifications": certs,
        "education": education,
        "work_history": _get("work_history", "experience", "jobs", default=[]),
    }
