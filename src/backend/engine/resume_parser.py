"""
Phase 8A — Semantic Resume Parser Engine
Parses JSON and PDF resumes into a normalised UserProfile dict.

Upgrade over Phase 1:
- Semantic role inference: maps job title → implied professional competencies
  (IT Audit Manager implies SOX/ITGC/COBIT even if not mentioned)
- Post-Doc / Research track: maps academic roles → grant-writing, IRB, etc.
- Experience year extraction from structured date ranges, not just year tokens
- Cert normalisation: maps aliases ("Certified Information Systems Auditor" → "CISA")
- Summary / bio used for additional context inference

Public API:
  parse_resume_bytes(content: bytes, content_type: str) -> dict
  parse_resume_file(path: str) -> dict
"""
import json
import re
from typing import Any, Dict, List, Optional


# ─── Semantic Role → Skill Inference Tables ──────────────────────────────────
# Maps role title patterns (lowercase, partial match) to implied skills.
# "Implied" means: a professional in that role is expected to know these things
# even if the resume never explicitly lists them.

_ROLE_SKILL_MAP: Dict[str, List[str]] = {
    # IT Audit
    "it audit":           ["SOX Compliance", "ITGC", "COBIT", "Risk Management",
                           "Internal Audit", "IIA Standards", "Control Testing",
                           "CISA", "Audit Planning", "COSO Framework"],
    "audit manager":      ["SOX Compliance", "ITGC", "Audit Planning", "Team Leadership",
                           "Stakeholder Management", "Risk Assessment", "COSO Framework"],
    "internal audit":     ["Risk Assessment", "Control Testing", "IIA Standards",
                           "Audit Workpapers", "Audit Committee Reporting"],
    "external audit":     ["GAAP", "GAAS", "Financial Statement Audit", "PCAOB Standards"],
    "compliance":         ["Regulatory Compliance", "Policy Development", "Risk Management",
                           "ISO 27001", "SOX Compliance", "GDPR"],
    "information security": ["NIST", "ISO 27001", "Threat Modeling", "SIEM",
                              "Incident Response", "Vulnerability Management"],
    "security analyst":   ["SIEM", "Threat Intelligence", "Incident Response",
                           "NIST", "Vulnerability Scanning", "Security Operations"],
    "ai governance":      ["AI Risk Management", "NIST AI RMF", "EU AI Act",
                           "Model Risk Management", "Algorithmic Auditing", "AIGP"],
    "risk manager":       ["Enterprise Risk Management", "Risk Frameworks", "COSO",
                           "Risk Quantification", "FAIR Model", "Risk Reporting"],
    "data analyst":       ["SQL", "Python", "Power BI", "Tableau", "Data Visualization",
                           "Statistical Analysis", "ETL"],
    "data scientist":     ["Python", "Machine Learning", "TensorFlow", "SQL",
                           "Statistical Modeling", "Feature Engineering", "MLOps"],
    "cloud engineer":     ["AWS", "Azure", "GCP", "Terraform", "Kubernetes",
                           "CI/CD", "Infrastructure as Code"],
    "devops":             ["CI/CD", "Docker", "Kubernetes", "Jenkins", "Terraform",
                           "Linux", "Bash", "Monitoring"],
    "software engineer":  ["Python", "Java", "SQL", "Git", "REST API",
                           "System Design", "Testing"],
    "product manager":    ["Product Roadmap", "Agile", "Stakeholder Management",
                           "User Research", "OKRs", "Jira"],
    # Academic / Research
    "post-doc":           ["Grant Writing", "IRB Compliance", "Statistical Analysis",
                           "Peer Review", "R", "Python", "Literature Review",
                           "Lab Management", "Research Design", "Publications"],
    "postdoctoral":       ["Grant Writing", "IRB Compliance", "Statistical Analysis",
                           "Peer Review", "R", "Python", "Literature Review",
                           "Lab Management", "Research Design", "Publications"],
    "research scientist": ["Experimental Design", "Data Analysis", "Publications",
                           "Grant Writing", "Statistical Modeling", "R", "Python"],
    "research associate": ["Literature Review", "Data Collection", "Statistical Analysis",
                           "Lab Techniques", "Report Writing"],
    "professor":          ["Curriculum Development", "Grant Writing", "Peer Review",
                           "Teaching", "Research Supervision", "Publications"],
    "principal investigator": ["NSF/NIH Grant Management", "Research Design",
                                "Budget Management", "IRB Compliance", "Lab Management"],
    "lab manager":        ["Lab Safety Compliance", "SOPs", "Equipment Maintenance",
                           "Inventory Management", "IRB Compliance"],
    # Healthcare / Life Sciences
    "clinical researcher": ["Clinical Trials", "GCP", "IRB Compliance", "FDA Regulations",
                             "Data Management", "HIPAA"],
    "pharmacist":         ["Drug Interactions", "Patient Counseling", "HIPAA",
                           "Pharmacy Regulations", "Clinical Knowledge"],
    # Finance
    "financial analyst":  ["Financial Modeling", "Excel", "DCF Analysis", "SQL",
                           "Bloomberg", "Forecasting", "Variance Analysis"],
    "controller":         ["GAAP", "Financial Reporting", "ERP Systems", "Month-End Close",
                           "Internal Controls", "Budgeting"],
}

# ─── Cert alias normalisation ─────────────────────────────────────────────────
_CERT_ALIASES: Dict[str, str] = {
    # Full name → acronym
    "certified information systems auditor":  "CISA",
    "certified internal auditor":             "CIA",
    "certified public accountant":            "CPA",
    "certified information security manager": "CISM",
    "certified in risk and information systems control": "CRISC",
    "certified in governance of enterprise it": "CGEIT",
    "certified cloud security professional":  "CCSP",
    "ai governance professional":             "AIGP",
    "associate ai auditor":                   "AAIA",
    "certified information systems security professional": "CISSP",
    "project management professional":        "PMP",
    "certified scrum master":                 "CSM",
    "six sigma green belt":                   "SSGB",
    "six sigma black belt":                   "SSBB",
    # Acronym self-maps (so input "cisa" → "CISA")
    "cisa":  "CISA",
    "ccsp":  "CCSP",
    "cissp": "CISSP",
    "cism":  "CISM",
    "crisc": "CRISC",
    "aigp":  "AIGP",
    "aaia":  "AAIA",
    "pmp":   "PMP",
    "cpa":   "CPA",
    "cia":   "CIA",
    "cgeit": "CGEIT",
    "csm":   "CSM",
    # Partial / phrase variants
    "ai governance prof":            "AIGP",
    "information systems auditor":   "CISA",
    "cloud security professional":   "CCSP",
    "information systems security":  "CISSP",
    "certified fraud examiner":      "CFE",
    "financial risk manager":        "FRM",
    # Common dotted abbreviations
    "c.i.s.a":  "CISA",
    "c.c.s.p":  "CCSP",
    "c.i.s.s.p": "CISSP",
}

# ─── Skill keyword corpus (kept for raw-text extraction) ─────────────────────
_SKILL_KEYWORDS = {
    "SOX", "ITGC", "CISA", "CISM", "CGEIT", "CRISC", "CCSP", "AIGP",
    "Risk Management", "Internal Audit", "External Audit", "Compliance",
    "Segregation of Duties", "SoD", "IT Audit", "COBIT", "ISO 27001",
    "Python", "SQL", "Excel", "Power BI", "Tableau", "JIRA", "ServiceNow",
    "Azure", "AWS", "GCP", "Machine Learning", "AI", "Data Analysis",
    "Grant Writing", "IRB", "Statistical Analysis", "R", "Lab Management",
    "NIST", "GDPR", "HIPAA", "FDA", "GCP", "Terraform", "Docker", "Kubernetes",
    "FAIR Model", "AI Governance", "NIST AI RMF", "EU AI Act",
}

_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[a-z]{2,}", re.I)
_PHONE_RE = re.compile(r"[\+\d][\d\s\-\(\)]{7,15}\d")
_YEAR_RE  = re.compile(r"\b(19|20)\d{2}\b")

# ─── Cert scan patterns (full-text scan, not just structured fields) ──────────
_CERT_SCAN_PATTERNS = [
    (re.compile(r'\bCISA\b'),   "CISA"),
    (re.compile(r'\bCCSP\b'),   "CCSP"),
    (re.compile(r'\bCISM\b'),   "CISM"),
    (re.compile(r'\bCISSP\b'),  "CISSP"),
    (re.compile(r'\bCRISC\b'),  "CRISC"),
    (re.compile(r'\bCGEIT\b'),  "CGEIT"),
    (re.compile(r'\bAIGP\b'),   "AIGP"),
    (re.compile(r'\bAAIA\b'),   "AAIA"),
    # CIA excluding "CIA triad" to avoid false positives
    (re.compile(r'\bCIA\b(?!\s+triad)', re.I), "CIA"),
    (re.compile(r'\bPMP\b'),    "PMP"),
    (re.compile(r'\bCPA\b'),    "CPA"),
    (re.compile(r'\bCFE\b'),    "CFE"),
    (re.compile(r'\bFRM\b'),    "FRM"),
    (re.compile(r'Certified Information Systems Auditor', re.I), "CISA"),
    (re.compile(r'Certified Cloud Security Professional', re.I), "CCSP"),
    (re.compile(r'AI Governance Professional', re.I), "AIGP"),
]


def _scan_text_for_certs(text: str) -> List[Dict]:
    """
    Scan raw text for certification acronyms and full names.
    Returns deduplicated list of cert dicts suitable for _normalise().
    """
    found: dict = {}
    for pattern, acronym in _CERT_SCAN_PATTERNS:
        if pattern.search(text):
            found[acronym] = {"name": acronym, "status": "Active", "issuer": ""}
    return list(found.values())


# ─── Public entry points ──────────────────────────────────────────────────────
def parse_resume_bytes(content: bytes, content_type: str) -> Dict[str, Any]:
    """
    Dispatch to the correct parser based on MIME type.
    Returns a semantically-enriched normalised profile dict.
    Edge cases: empty content, corrupt PDF, invalid JSON — all return safe defaults.
    """
    if not content or not content.strip():
        return _normalise({})   # empty upload → safe defaults, no crash
    if "json" in content_type:
        return _parse_json(content)
    if "pdf" in content_type:
        return _parse_pdf(content)
    try:
        return _parse_json(content)
    except Exception:
        return _parse_raw_text(content.decode("utf-8", errors="ignore"))


def parse_resume_file(path: str) -> Dict[str, Any]:
    """Convenience wrapper for local file paths."""
    with open(path, "rb") as f:
        content = f.read()
    content_type = "application/json" if path.endswith(".json") else "application/pdf"
    return parse_resume_bytes(content, content_type)


# ─── JSON parser ──────────────────────────────────────────────────────────────
def _parse_json(content: bytes) -> Dict[str, Any]:
    try:
        return _normalise(json.loads(content))
    except (json.JSONDecodeError, ValueError):
        return _parse_raw_text(content.decode("utf-8", errors="ignore"))


# ─── PDF parser ───────────────────────────────────────────────────────────────
def _parse_pdf(content: bytes) -> Dict[str, Any]:
    try:
        import pdfplumber
        import io
        pages = []
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page in pdf.pages:
                pages.append(page.extract_text() or "")
        text = "\n".join(pages)
        if not text.strip():
            return _normalise({})   # empty/image-only PDF — return safe defaults
        return _parse_raw_text(text)
    except ImportError:
        raise RuntimeError(
            "pdfplumber is required for PDF parsing. "
            "Install it with: pip install pdfplumber"
        )
    except Exception:
        return _normalise({})       # corrupt / password-protected PDF — safe defaults


# ─── Text heuristic extractor ─────────────────────────────────────────────────
def _parse_raw_text(text: str) -> Dict[str, Any]:
    lines     = [line.strip() for line in text.splitlines() if line.strip()]
    email     = next(iter(_EMAIL_RE.findall(text)), None)
    phone     = next(iter(_PHONE_RE.findall(text)), None)
    years     = [int(y) for y in _YEAR_RE.findall(text)]
    exp_years = (max(years) - min(years)) if len(years) >= 2 else None
    skills    = [kw for kw in _SKILL_KEYWORDS if kw.lower() in text.lower()]

    # Detect current role from first few lines
    current_role = _detect_role_from_text(lines[:5])

    # Scan full text for certification mentions
    text_certs = _scan_text_for_certs(text)

    return _normalise({
        "name":             lines[0] if lines else "Unknown",
        "email":            email,
        "phone":            phone,
        "current_role":     current_role,
        "experience_years": exp_years,
        "skills":           skills,
        "certifications":   text_certs,
        "raw_text":         text[:2000],
    })


# ─── Semantic inference ───────────────────────────────────────────────────────
def _infer_skills_from_role(role: Optional[str], summary: Optional[str] = None) -> List[str]:
    """
    Given a job title (and optional summary), return implied professional skills
    the candidate is expected to have based on industry knowledge.
    """
    if not role:
        return []

    combined = f"{role} {summary or ''}".lower()
    inferred: List[str] = []

    for role_pattern, skills in _ROLE_SKILL_MAP.items():
        if role_pattern in combined:
            inferred.extend(skills)

    # Deduplicate preserving order
    seen = set()
    result = []
    for s in inferred:
        if s not in seen:
            seen.add(s)
            result.append(s)
    return result


def _normalise_cert(cert_entry: Any) -> Dict[str, Any]:
    """
    Normalise a certification entry: expand aliases, ensure consistent schema.
    Accepts a string ("CISA") or a dict {"name": "...", "issuer": "...", "status": "..."}.
    """
    if isinstance(cert_entry, str):
        name = cert_entry.strip()
        normalised = _CERT_ALIASES.get(name.lower(), name)
        return {"name": normalised, "full_name": name, "status": "Active", "issuer": ""}
    if isinstance(cert_entry, dict):
        raw_name  = cert_entry.get("name", "")
        full_name = cert_entry.get("full_name", raw_name)
        normalised = _CERT_ALIASES.get(full_name.lower(), _CERT_ALIASES.get(raw_name.lower(), raw_name))
        return {
            "name":       normalised,
            "full_name":  full_name or raw_name,
            "status":     cert_entry.get("status", "Active"),
            "issuer":     cert_entry.get("issuer", ""),
            "acquired":   cert_entry.get("acquired", ""),
        }
    return {}


def _detect_role_from_text(lines: List[str]) -> Optional[str]:
    """Scan the first few lines of a text resume for a plausible job title."""
    role_signals = ["manager", "analyst", "engineer", "director", "researcher",
                    "auditor", "consultant", "scientist", "developer", "specialist"]
    for line in lines:
        if any(sig in line.lower() for sig in role_signals) and len(line.split()) <= 8:
            return line
    return None


def _compute_experience_years(raw: Dict[str, Any]) -> Optional[int]:
    """
    Try multiple strategies to extract years of experience:
    1. Explicit field (experience_years / years_of_experience)
    2. Date range calculation from work history
    3. Year token extraction from raw text
    """
    explicit = raw.get("experience_years") or raw.get("years_of_experience")
    if explicit:
        try:
            return int(explicit)
        except (ValueError, TypeError):
            pass

    # Try work history date ranges
    history = raw.get("work_history") or raw.get("experience") or []
    if isinstance(history, list) and history:
        years = []
        for entry in history:
            if isinstance(entry, dict):
                start = entry.get("start_year") or entry.get("from_year")
                end   = entry.get("end_year") or entry.get("to_year") or 2026
                if start:
                    try:
                        years.extend([int(start), int(end)])
                    except (ValueError, TypeError):
                        pass
        if len(years) >= 2:
            return max(years) - min(years)

    # Fall back to year token heuristic on raw text if available
    raw_text = raw.get("raw_text", "")
    if raw_text:
        found = [int(y) for y in _YEAR_RE.findall(raw_text)]
        if len(found) >= 2:
            return max(found) - min(found)

    return None


# ─── Schema normaliser ────────────────────────────────────────────────────────
def _normalise(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Coerce arbitrary resume dicts into a consistent schema enriched with
    semantic skill inference from job title and summary.
    """
    current_role = raw.get("current_role") or raw.get("title")
    summary      = raw.get("summary") or raw.get("bio") or raw.get("about")
    explicit_skills = _to_list(raw.get("skills"))

    # Semantic inference: role → implied skills
    inferred = _infer_skills_from_role(current_role, summary)

    # Merge: explicit skills first, then inferred (no duplicates, case-insensitive)
    explicit_lower = {s.lower() for s in explicit_skills}
    merged_skills  = list(explicit_skills)
    for s in inferred:
        if s.lower() not in explicit_lower:
            merged_skills.append(s)
            explicit_lower.add(s.lower())

    # Normalise certifications
    raw_certs = _to_list(raw.get("certifications") or raw.get("certs"))
    certs     = [_normalise_cert(c) for c in raw_certs if c]

    return {
        "name":             raw.get("name") or raw.get("full_name", "Unknown"),
        "email":            raw.get("email"),
        "phone":            raw.get("phone"),
        "current_role":     current_role,
        "target_role":      raw.get("target_role"),
        "experience_years": _compute_experience_years(raw),
        "location":         raw.get("location"),
        "skills":           merged_skills,
        "inferred_skills":  inferred,
        "certifications":   certs,
        "education":        _to_list(raw.get("education")),
        "summary":          summary,
        "raw":              raw,
    }


def _to_list(val: Any) -> list:
    if val is None:
        return []
    if isinstance(val, list):
        return val
    return [val]
