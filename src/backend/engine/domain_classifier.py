"""
Profile Domain Classifier
=========================
Reads any normalised profile dict and returns a domain key that drives
all downstream outputs: cert recommendations, job mock fallback,
artifact generation, and market intelligence signals.

Public API:
    classify(profile: dict) -> str          — domain key
    domain_label(domain: str) -> str        — human-readable label
    get_domain_cert_catalog(domain: str) -> list[dict]  — cert list
    get_domain_mock_jobs(domain: str, market: str) -> list[dict]  — mock jobs
"""

from datetime import datetime
from typing import Any, Dict, List


# ── Domain signal tables ───────────────────────────────────────────────────────
# Each domain has role_keywords (strong signal, 3 pts each) and
# skill_keywords (supporting signal, 1 pt each).

_DOMAIN_SIGNALS: Dict[str, Dict[str, List[str]]] = {
    "it_audit": {
        "role_keywords": [
            "it audit", "internal audit", "external audit", "compliance manager",
            "grc manager", "ai governance", "risk manager", "information security",
            "security analyst", "audit manager", "audit director", "ciso",
            "chief audit", "controls", "sox manager", "it risk",
        ],
        "skill_keywords": [
            "sox", "itgc", "cisa", "cobit", "grc", "iso 27001", "nist",
            "crisc", "cgeit", "sod", "itac", "audit committee", "pcaob",
            "regulatory compliance", "internal controls",
        ],
    },
    "research_academia": {
        "role_keywords": [
            "postdoc", "post-doc", "postdoctoral", "research scientist",
            "research associate", "principal investigator", "professor",
            "lab manager", "research fellow", "phd student", "staff scientist",
            "research director", "associate professor", "assistant professor",
            "clinical researcher", "biologist", "biochemist", "geneticist",
        ],
        "skill_keywords": [
            "rna-seq", "crispr", "irb", "grant writing", "peer review",
            "publications", "western blot", "pcr", "ngs", "bioinformatics",
            "cell culture", "flow cytometry", "mass spectrometry", "r",
            "stata", "grant", "lab management", "nih", "nsf", "literature review",
        ],
    },
    "data_science": {
        "role_keywords": [
            "data scientist", "machine learning engineer", "ml engineer",
            "ai engineer", "deep learning", "nlp engineer", "data engineer",
            "ai researcher", "ml researcher", "applied scientist",
        ],
        "skill_keywords": [
            "tensorflow", "pytorch", "scikit-learn", "mlops", "spark",
            "databricks", "hugging face", "transformers", "model training",
            "feature engineering", "xgboost", "lightgbm", "neural network",
            "deep learning", "machine learning",
        ],
    },
    "engineering": {
        "role_keywords": [
            "software engineer", "software developer", "devops engineer",
            "site reliability", "sre", "cloud engineer", "backend engineer",
            "frontend engineer", "full stack", "platform engineer",
            "systems engineer",
        ],
        "skill_keywords": [
            "kubernetes", "docker", "ci/cd", "terraform", "java",
            "node.js", "react", "system design", "microservices",
            "rest api", "graphql", "golang", "rust",
        ],
    },
    "healthcare": {
        "role_keywords": [
            "nurse", "physician", "doctor", "clinical researcher",
            "pharmacist", "clinical trial", "medical officer",
            "healthcare administrator", "clinical coordinator",
            "healthcare quality", "clinical operations",
        ],
        "skill_keywords": [
            "hipaa", "fda", "clinical trials", "patient care", "medical coding",
            "emr", "ehr", "icd-10", "cpt codes", "clinical documentation",
            "pharmacy", "gcp clinical", "regulatory submissions",
        ],
    },
    "finance": {
        "role_keywords": [
            "financial analyst", "investment banker", "portfolio manager",
            "actuary", "controller", "cfo", "treasury analyst",
            "equity analyst", "quant analyst", "credit analyst",
        ],
        "skill_keywords": [
            "dcf", "bloomberg", "valuation", "financial modeling", "cfa",
            "frm", "derivatives", "trading", "private equity",
            "hedge fund", "credit risk", "gaap", "ifrs",
        ],
    },
    "product": {
        "role_keywords": [
            "product manager", "product owner", "ux designer",
            "scrum master", "agile coach", "product lead",
        ],
        "skill_keywords": [
            "product roadmap", "user research", "okrs", "jira", "figma",
            "a/b testing", "user stories", "sprint planning",
        ],
    },
}


def _score_profile(profile: Dict[str, Any]) -> Dict[str, int]:
    """Internal: compute domain scores for a profile dict."""
    role     = (profile.get("current_role") or profile.get("target_role") or "").lower()
    skills   = " ".join(str(s) for s in profile.get("skills", [])).lower()
    summary  = (profile.get("summary") or "").lower()
    edu      = " ".join(
        (e.get("field", "") if isinstance(e, dict) else str(e))
        for e in profile.get("education", [])
    ).lower()
    combined = f"{role} {skills} {summary} {edu}"

    scores: Dict[str, int] = {domain: 0 for domain in _DOMAIN_SIGNALS}
    for domain, signals in _DOMAIN_SIGNALS.items():
        for kw in signals["role_keywords"]:
            if kw in role:
                scores[domain] += 3
        for kw in signals["skill_keywords"]:
            if kw in combined:
                scores[domain] += 1
    return scores


def classify(profile: Dict[str, Any]) -> str:
    """
    Classify a normalised profile dict into the most relevant domain.
    Returns a domain key (string). Falls back to 'it_audit' if no clear signal.

    Scoring: role keyword match = 3 pts, skill keyword match = 1 pt.
    Domain with highest total score wins (minimum threshold: 2 pts).
    """
    scores = _score_profile(profile)
    best = max(scores, key=lambda d: scores[d])
    return best if scores[best] >= 2 else "it_audit"


def classify_full(profile: Dict[str, Any]) -> Dict[str, Any]:
    """
    Returns primary domain AND secondary domain (if score >= 2).
    Used for cross-domain cert bridging and richer sidebar context.

    Returns: {"primary": str, "secondary": str | None}
    """
    scores = _score_profile(profile)
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    primary   = ranked[0][0] if ranked[0][1] >= 2 else "it_audit"
    secondary = (
        ranked[1][0]
        if len(ranked) > 1 and ranked[1][1] >= 2 and ranked[1][0] != primary
        else None
    )
    return {"primary": primary, "secondary": secondary}


def domain_label(domain: str) -> str:
    return {
        "it_audit":          "IT Audit & Governance",
        "research_academia": "Research & Academia",
        "data_science":      "Data Science & AI/ML",
        "engineering":       "Software Engineering",
        "healthcare":        "Healthcare & Clinical",
        "finance":           "Finance & Investment",
        "product":           "Product & Design",
    }.get(domain, "Professional")


# ── Multi-domain cert catalog ──────────────────────────────────────────────────
# Each entry mirrors the certifications_catalog.json schema minimally:
# id, acronym, name, issuer, study_weeks, exam_questions, priority, tier, rationale, domains

_DOMAIN_CERT_CATALOG: Dict[str, List[Dict[str, Any]]] = {

    "it_audit": [],  # served from certifications_catalog.json via certification_engine

    "research_academia": [
        {
            "id": "gcp_research", "acronym": "GCP", "tier": "immediate",
            "name": "Good Clinical Practice (ICH E6 R2)",
            "issuer": "NIH / FDA / ICH",
            "study_weeks": "4–6 weeks", "exam_questions": 50, "priority": "critical",
            "rationale": "Required for all NIH-funded research involving human subjects. Validates protocol adherence and research ethics standards.",
            "salary_premium_usd": 15000, "trend": "Rising",
            "domains": [
                {"id":"gcp-d1","name":"Research Ethics & IRB","weight_pct":25,
                 "topics":["IRB protocol","Informed consent","Human subjects protection","Belmont Report"]},
                {"id":"gcp-d2","name":"Clinical Trial Design","weight_pct":25,
                 "topics":["Phase I–IV trials","Randomisation","Blinding","Sample size"]},
                {"id":"gcp-d3","name":"Data Integrity & Reporting","weight_pct":25,
                 "topics":["CRF completion","Adverse event reporting","Audit trail","ALCOA principles"]},
                {"id":"gcp-d4","name":"Regulatory Compliance","weight_pct":25,
                 "topics":["FDA 21 CFR Part 50","ICH E6 R2","GCP inspection readiness","Protocol deviations"]},
            ],
        },
        {
            "id": "citi_research", "acronym": "CITI", "tier": "immediate",
            "name": "CITI Program – Research Integrity & Ethics",
            "issuer": "CITI Program",
            "study_weeks": "2–4 weeks", "exam_questions": 40, "priority": "critical",
            "rationale": "Mandatory for NIH-funded investigators. Covers responsible conduct of research and human subjects protection.",
            "salary_premium_usd": 0, "trend": "Stable",
            "domains": [
                {"id":"citi-d1","name":"Responsible Conduct of Research","weight_pct":40,
                 "topics":["Research misconduct","Data management","Authorship","Conflicts of interest"]},
                {"id":"citi-d2","name":"Human Subjects Protection","weight_pct":35,
                 "topics":["Belmont Report","Vulnerable populations","Consent processes","Risk/benefit analysis"]},
                {"id":"citi-d3","name":"Research Ethics","weight_pct":25,
                 "topics":["Publication ethics","Mentoring","Lab practices","Research integrity"]},
            ],
        },
        {
            "id": "nih_grant", "acronym": "NIH-GW", "tier": "immediate",
            "name": "NIH Grant Writing Fundamentals (R01/R21)",
            "issuer": "NIH Office of Research Training",
            "study_weeks": "6–10 weeks", "exam_questions": 20, "priority": "high",
            "rationale": "R01/R21 grants are the primary NIH funding mechanism. Structured preparation reduces resubmission cycles by ~40%.",
            "salary_premium_usd": 0, "trend": "Rising",
            "domains": [
                {"id":"nihgw-d1","name":"Specific Aims & Significance","weight_pct":30,
                 "topics":["Hypothesis framing","Innovation statement","Gap identification","Significance statement"]},
                {"id":"nihgw-d2","name":"Research Strategy","weight_pct":40,
                 "topics":["Approach design","Preliminary data","Timeline","Rigor & reproducibility","Alternatives"]},
                {"id":"nihgw-d3","name":"Budget & Administration","weight_pct":30,
                 "topics":["Modular vs detailed budget","Subcontracts","Progress reports","Project narrative"]},
            ],
        },
        {
            "id": "bioinformatics_cert", "acronym": "BINFO", "tier": "midterm",
            "name": "Applied Bioinformatics Certification",
            "issuer": "EMBL-EBI / Coursera",
            "study_weeks": "8–12 weeks", "exam_questions": 30, "priority": "high",
            "rationale": "Validates computational biology skills (RNA-seq, variant calling, pathway analysis) that are increasingly required for grant renewal.",
            "salary_premium_usd": 20000, "trend": "Rising",
            "domains": [
                {"id":"binfo-d1","name":"Genomics & NGS Analysis","weight_pct":35,
                 "topics":["RNA-seq pipeline","Variant calling","GATK","DESeq2","edgeR","kallisto"]},
                {"id":"binfo-d2","name":"Statistical Methods","weight_pct":30,
                 "topics":["Differential expression","GSEA","Multiple testing correction","PCA","Clustering"]},
                {"id":"binfo-d3","name":"Tools & Workflow Automation","weight_pct":35,
                 "topics":["Python","R","Snakemake","Nextflow","STAR","HISAT2","Salmon","IGV"]},
            ],
        },
    ],

    "data_science": [
        {
            "id": "aws_ml", "acronym": "AWS-MLS", "tier": "immediate",
            "name": "AWS Certified Machine Learning – Specialty",
            "issuer": "Amazon Web Services",
            "study_weeks": "8–12 weeks", "exam_questions": 65, "priority": "critical",
            "rationale": "Most recognised cloud ML cert. Validates end-to-end ML pipelines on AWS (SageMaker, Bedrock, Feature Store).",
            "salary_premium_usd": 30000, "trend": "Rising",
            "domains": [
                {"id":"awsml-d1","name":"Data Engineering","weight_pct":20,
                 "topics":["S3","Glue","Feature Store","ETL","Lake Formation","Athena"]},
                {"id":"awsml-d2","name":"Modelling & Algorithm Selection","weight_pct":36,
                 "topics":["XGBoost","Neural networks","SageMaker AutoML","Hyperparameter tuning","Model evaluation"]},
                {"id":"awsml-d3","name":"ML Implementation & Operations","weight_pct":24,
                 "topics":["MLflow","Real-time endpoints","Batch transform","Model monitoring","A/B testing"]},
                {"id":"awsml-d4","name":"ML Security & Compliance","weight_pct":20,
                 "topics":["IAM","VPC endpoints","Data encryption","Responsible AI","Model cards"]},
            ],
        },
        {
            "id": "tensorflow_dev", "acronym": "TF-DEV", "tier": "immediate",
            "name": "TensorFlow Developer Certificate",
            "issuer": "Google / TensorFlow",
            "study_weeks": "6–8 weeks", "exam_questions": 5, "priority": "high",
            "rationale": "Validates practical deep learning skills: CNNs, NLP, time series. Recognised globally across AI teams.",
            "salary_premium_usd": 20000, "trend": "Stable",
            "domains": [
                {"id":"tfdev-d1","name":"TF Fundamentals","weight_pct":25,
                 "topics":["Tensors","Keras API","Sequential & Functional API","Model save/load"]},
                {"id":"tfdev-d2","name":"Image Classification","weight_pct":25,
                 "topics":["CNNs","Transfer learning","ImageDataGenerator","Data augmentation"]},
                {"id":"tfdev-d3","name":"NLP with TF","weight_pct":25,
                 "topics":["Tokenisation","Word embeddings","LSTM","Text classification","Transformers"]},
                {"id":"tfdev-d4","name":"Time Series & Sequences","weight_pct":25,
                 "topics":["RNNs","LSTM","WaveNet","Forecasting","Sequence-to-sequence"]},
            ],
        },
        {
            "id": "azure_ds", "acronym": "DP-100", "tier": "midterm",
            "name": "Azure Data Scientist Associate (DP-100)",
            "issuer": "Microsoft",
            "study_weeks": "8–10 weeks", "exam_questions": 60, "priority": "high",
            "rationale": "Required at Microsoft-stack organisations. Covers Azure ML Studio, AutoML, Responsible AI dashboard.",
            "salary_premium_usd": 25000, "trend": "Rising",
            "domains": [
                {"id":"dp100-d1","name":"Design & Prepare ML Solution","weight_pct":20,
                 "topics":["Azure ML workspace","Compute clusters","Data assets","Datastores"]},
                {"id":"dp100-d2","name":"Experiment & Train Models","weight_pct":35,
                 "topics":["AutoML","Designer","MLflow tracking","Hyperparameter tuning","Pipelines"]},
                {"id":"dp100-d3","name":"Deploy & Operate ML Solutions","weight_pct":45,
                 "topics":["Batch/real-time endpoints","Model monitoring","Responsible AI dashboard","Data drift"]},
            ],
        },
    ],

    "engineering": [
        {
            "id": "ckad", "acronym": "CKAD", "tier": "immediate",
            "name": "Certified Kubernetes Application Developer",
            "issuer": "CNCF / Linux Foundation",
            "study_weeks": "8–10 weeks", "exam_questions": 19, "priority": "critical",
            "rationale": "Industry standard for cloud-native development. Practical hands-on exam — no multiple choice.",
            "salary_premium_usd": 25000, "trend": "Rising",
            "domains": [
                {"id":"ckad-d1","name":"Application Design & Build","weight_pct":20,
                 "topics":["Containers","Multi-container pods","Init containers","Jobs/CronJobs"]},
                {"id":"ckad-d2","name":"Application Deployment","weight_pct":20,
                 "topics":["Deployments","Rolling updates","Helm","Kustomize","Blue-green"]},
                {"id":"ckad-d3","name":"Application Observability","weight_pct":15,
                 "topics":["Liveness/readiness probes","Logging","Metrics","Debug techniques"]},
                {"id":"ckad-d4","name":"Environment & Configuration","weight_pct":25,
                 "topics":["ConfigMaps","Secrets","Security contexts","Resource limits","Namespaces"]},
                {"id":"ckad-d5","name":"Services & Networking","weight_pct":20,
                 "topics":["Services","Ingress","Network policies","CoreDNS","Service mesh basics"]},
            ],
        },
        {
            "id": "aws_saa", "acronym": "AWS-SAA", "tier": "immediate",
            "name": "AWS Solutions Architect – Associate",
            "issuer": "Amazon Web Services",
            "study_weeks": "8–12 weeks", "exam_questions": 65, "priority": "critical",
            "rationale": "Most widely-held cloud cert. Required at 70%+ of cloud engineering roles globally.",
            "salary_premium_usd": 28000, "trend": "Stable",
            "domains": [
                {"id":"awssaa-d1","name":"Secure Architectures","weight_pct":30,
                 "topics":["IAM","KMS","VPC security groups","AWS Inspector","GuardDuty","SCPs"]},
                {"id":"awssaa-d2","name":"Resilient Architectures","weight_pct":26,
                 "topics":["Multi-AZ","Auto Scaling","ELB","Route 53","RDS failover","S3 versioning"]},
                {"id":"awssaa-d3","name":"High-Performing Architectures","weight_pct":24,
                 "topics":["EC2","Lambda","ECS/EKS","DynamoDB","ElastiCache","CloudFront"]},
                {"id":"awssaa-d4","name":"Cost-Optimised Architectures","weight_pct":20,
                 "topics":["Reserved instances","Spot Fleet","S3 lifecycle tiers","Cost Explorer","Savings Plans"]},
            ],
        },
    ],

    "healthcare": [
        {
            "id": "cphq", "acronym": "CPHQ", "tier": "immediate",
            "name": "Certified Professional in Healthcare Quality",
            "issuer": "NAHQ",
            "study_weeks": "10–14 weeks", "exam_questions": 140, "priority": "critical",
            "rationale": "Gold standard for healthcare quality professionals. Required at most hospital quality improvement roles.",
            "salary_premium_usd": 18000, "trend": "Stable",
            "domains": [
                {"id":"cphq-d1","name":"Healthcare Data Analytics","weight_pct":19,
                 "topics":["Statistical process control","Data visualisation","Outcome measures","Benchmarking"]},
                {"id":"cphq-d2","name":"Performance & Process Improvement","weight_pct":23,
                 "topics":["PDSA cycle","Lean/Six Sigma","Root cause analysis","FMEA","Kaizen"]},
                {"id":"cphq-d3","name":"Healthcare Regulatory Environment","weight_pct":20,
                 "topics":["CMS Conditions of Participation","TJC standards","HIPAA","CMS quality reporting"]},
                {"id":"cphq-d4","name":"Patient Safety","weight_pct":19,
                 "topics":["Adverse events","Near-miss analysis","Safety culture","High-reliability organisations"]},
                {"id":"cphq-d5","name":"Quality Leadership","weight_pct":19,
                 "topics":["Strategic planning","Change management","Governance","Accreditation readiness"]},
            ],
        },
        {
            "id": "chda", "acronym": "CHDA", "tier": "midterm",
            "name": "Certified Health Data Analyst",
            "issuer": "AHIMA",
            "study_weeks": "8–12 weeks", "exam_questions": 130, "priority": "high",
            "rationale": "Validates expertise in health data analysis, coding, and clinical informatics. Rising demand with EHR adoption.",
            "salary_premium_usd": 15000, "trend": "Rising",
            "domains": [
                {"id":"chda-d1","name":"Health Data Structure & Standards","weight_pct":35,
                 "topics":["ICD-10-CM/PCS","CPT codes","HL7 FHIR","SNOMED CT","LOINC"]},
                {"id":"chda-d2","name":"Data Analytics & Reporting","weight_pct":35,
                 "topics":["SQL","Tableau","Healthcare dashboards","Predictive analytics","Population health"]},
                {"id":"chda-d3","name":"Privacy & Security","weight_pct":30,
                 "topics":["HIPAA","De-identification","Data governance","Breach notification","Risk assessment"]},
            ],
        },
    ],

    "finance": [
        {
            "id": "cfa_l1", "acronym": "CFA-L1", "tier": "immediate",
            "name": "CFA Level 1 – Chartered Financial Analyst",
            "issuer": "CFA Institute",
            "study_weeks": "16–20 weeks", "exam_questions": 180, "priority": "critical",
            "rationale": "Most prestigious global finance credential. Opens doors to buy-side, sell-side, and asset management globally.",
            "salary_premium_usd": 40000, "trend": "Stable",
            "domains": [
                {"id":"cfa1-d1","name":"Ethical & Professional Standards","weight_pct":15,
                 "topics":["CFA Code of Ethics","Standards of Professional Conduct","GIPS","Research objectivity"]},
                {"id":"cfa1-d2","name":"Quantitative Methods","weight_pct":8,
                 "topics":["TVM","Statistics","Regression","Simulation","Hypothesis testing"]},
                {"id":"cfa1-d3","name":"Financial Reporting & Analysis","weight_pct":13,
                 "topics":["IFRS vs GAAP","Financial statements","Quality of earnings","Ratio analysis"]},
                {"id":"cfa1-d4","name":"Equity & Fixed Income","weight_pct":20,
                 "topics":["DCF","Relative valuation","Bond pricing","Duration","Convexity","Credit risk"]},
                {"id":"cfa1-d5","name":"Portfolio Management","weight_pct":5,
                 "topics":["MPT","CAPM","Risk management","Investment Policy Statement"]},
            ],
        },
        {
            "id": "frm_p1", "acronym": "FRM-P1", "tier": "immediate",
            "name": "FRM Part 1 – Financial Risk Manager",
            "issuer": "GARP",
            "study_weeks": "12–16 weeks", "exam_questions": 100, "priority": "high",
            "rationale": "Leading risk management credential. Required at bank treasury, risk, and quantitative finance roles.",
            "salary_premium_usd": 30000, "trend": "Rising",
            "domains": [
                {"id":"frm1-d1","name":"Foundations of Risk Management","weight_pct":20,
                 "topics":["Risk governance","CAPM","ERM","Risk measurement"]},
                {"id":"frm1-d2","name":"Quantitative Analysis","weight_pct":20,
                 "topics":["Probability","Regression","Monte Carlo","Volatility models"]},
                {"id":"frm1-d3","name":"Financial Markets & Products","weight_pct":30,
                 "topics":["Derivatives","Futures","Options","Swaps","Fixed income"]},
                {"id":"frm1-d4","name":"Valuation & Risk Models","weight_pct":30,
                 "topics":["VaR","Credit risk models","Market risk","Basel III","Stress testing"]},
            ],
        },
    ],

    "product": [
        {
            "id": "pmp", "acronym": "PMP", "tier": "immediate",
            "name": "Project Management Professional",
            "issuer": "PMI",
            "study_weeks": "12–16 weeks", "exam_questions": 180, "priority": "critical",
            "rationale": "Globally recognised across all industries. Required at senior PM and product leadership roles.",
            "salary_premium_usd": 25000, "trend": "Stable",
            "domains": [
                {"id":"pmp-d1","name":"People","weight_pct":42,
                 "topics":["Team leadership","Conflict management","Stakeholder engagement","Agile teams","Coaching"]},
                {"id":"pmp-d2","name":"Process","weight_pct":50,
                 "topics":["Scope/schedule/cost","Risk management","Quality","Procurement","Agile ceremonies","Hybrid PM"]},
                {"id":"pmp-d3","name":"Business Environment","weight_pct":8,
                 "topics":["Strategic alignment","Benefits realisation","Compliance","Governance"]},
            ],
        },
        {
            "id": "csm", "acronym": "CSM", "tier": "immediate",
            "name": "Certified Scrum Master",
            "issuer": "Scrum Alliance",
            "study_weeks": "4–6 weeks", "exam_questions": 50, "priority": "high",
            "rationale": "Foundation for Agile teams. Required at most product and engineering organisations.",
            "salary_premium_usd": 15000, "trend": "Stable",
            "domains": [
                {"id":"csm-d1","name":"Scrum Theory & Principles","weight_pct":30,
                 "topics":["Empiricism","Transparency","Inspection","Adaptation","Scrum values"]},
                {"id":"csm-d2","name":"Scrum Events & Artifacts","weight_pct":35,
                 "topics":["Sprint","Daily Scrum","Sprint Review","Retrospective","Product Backlog","Definition of Done"]},
                {"id":"csm-d3","name":"Scrum Team Dynamics","weight_pct":35,
                 "topics":["Self-organising teams","Servant leadership","Cross-functional teams","Removing impediments"]},
            ],
        },
    ],
}


def get_domain_cert_catalog(domain: str) -> List[Dict[str, Any]]:
    """Return the cert catalog for a given domain."""
    return _DOMAIN_CERT_CATALOG.get(domain, [])


# ── Domain alt search terms (secondary Adzuna query) ──────────────────────────
# Used by job_recommendation.py to fire a second parallel Adzuna call with a
# broader / more-searchable role title when the primary role string is verbose.

_DOMAIN_ALT_SEARCH: Dict[str, str] = {
    "it_audit":          "AI Governance Auditor",
    "research_academia": "Principal Research Scientist",
    "data_science":      "Machine Learning Engineer",
    "engineering":       "Senior Software Engineer",
    "healthcare":        "Healthcare Quality Analyst",
    "finance":           "Quantitative Risk Analyst",
    "product":           "Senior Product Manager",
}


def get_domain_alt_search(domain: str) -> str:
    """Return a clean, searchable alt role title for the given domain."""
    return _DOMAIN_ALT_SEARCH.get(domain, "")


# ── Domain-specific Market Intelligence taxonomy labels ────────────────────────
# Used by the dashboard IntelligenceTab to render domain-aware headings.

_DOMAIN_INTELLIGENCE_LABELS: Dict[str, Dict[str, str]] = {
    "it_audit": {
        "jd_shift":        "JD Shift Report",
        "rising_skill":    "Rising Skill Demand",
        "declining_skill": "Declining Demand",
        "salary":          "Salary Benchmark",
        "hiring_cos":      "Top Hiring Companies",
    },
    "research_academia": {
        "jd_shift":        "Grant Funding Landscape",
        "rising_skill":    "Emerging Research Methods",
        "declining_skill": "Fading Methodologies",
        "salary":          "Grant & Salary Bands",
        "hiring_cos":      "Top Research Institutions",
    },
    "data_science": {
        "jd_shift":        "Model Deployment Trends",
        "rising_skill":    "Rising ML Frameworks",
        "declining_skill": "Declining Tech Stack",
        "salary":          "ML Engineer Salary Benchmark",
        "hiring_cos":      "Top AI Hiring Teams",
    },
    "engineering": {
        "jd_shift":        "Engineering Hiring Signals",
        "rising_skill":    "Rising Platform Demand",
        "declining_skill": "Legacy Stack Decline",
        "salary":          "Engineering Salary Benchmark",
        "hiring_cos":      "Top Engineering Teams",
    },
    "healthcare": {
        "jd_shift":        "Clinical Role Landscape",
        "rising_skill":    "Rising Clinical Skills",
        "declining_skill": "Declining Modalities",
        "salary":          "Clinical Salary Benchmark",
        "hiring_cos":      "Top Healthcare Systems",
    },
    "finance": {
        "jd_shift":        "Finance Hiring Signals",
        "rising_skill":    "Rising Quant Skills",
        "declining_skill": "Declining Finance Roles",
        "salary":          "Finance Salary Benchmark",
        "hiring_cos":      "Top Financial Institutions",
    },
    "product": {
        "jd_shift":        "Product Role Signals",
        "rising_skill":    "Rising PM Methods",
        "declining_skill": "Declining PM Frameworks",
        "salary":          "PM Salary Benchmark",
        "hiring_cos":      "Top Product Teams",
    },
}


def get_intelligence_labels(domain: str) -> Dict[str, str]:
    """Return domain-specific label strings for the Market Intelligence tab."""
    return _DOMAIN_INTELLIGENCE_LABELS.get(domain, _DOMAIN_INTELLIGENCE_LABELS["it_audit"])


# ── Domain-aware mock job sets ─────────────────────────────────────────────────

def get_domain_mock_jobs(domain: str, market: str = "US") -> List[Dict[str, Any]]:
    """
    Return domain-appropriate mock jobs when live APIs return no results.
    Falls back to IT audit jobs if domain has no mock set.
    """
    ts   = datetime.utcnow().isoformat()
    base = {"posted": ts, "source": "Mock", "match_score": 0, "skills_matched": []}

    if domain == "research_academia":
        jobs = _research_jobs_us() if market == "US" else _research_jobs_in()
    elif domain == "data_science":
        jobs = _data_science_jobs_us() if market == "US" else _data_science_jobs_in()
    elif domain == "engineering":
        jobs = _engineering_jobs_us()
    elif domain == "healthcare":
        jobs = _healthcare_jobs_us()
    elif domain == "finance":
        jobs = _finance_jobs_us()
    else:
        return []  # caller falls back to existing IT audit mocks

    return [{**base, **j, "market": market} for j in jobs]


def _research_jobs_us() -> List[Dict]:
    return [
        {"id":"res-us-001","title":"Postdoctoral Fellow – Molecular Genetics",
         "company":"Lundquist Institute / Harbor-UCLA","location":"Torrance, CA",
         "salary_min":58_000,"salary_max":70_000,
         "description":"RNA-seq, CRISPR-Cas9, and single-cell transcriptomics research. NIH R01-funded lab. IRB protocols, grant co-authorship opportunities.",
         "tags":["RNA-seq","CRISPR","IRB","NIH","Python","R"],
         "url":"https://lundquistinstitute.org/jobs/"},
        {"id":"res-us-002","title":"Research Scientist II – Genomics",
         "company":"Genentech","location":"South San Francisco, CA (Hybrid)",
         "salary_min":130_000,"salary_max":165_000,
         "description":"Lead NGS pipeline development, variant analysis, and functional genomics. CRISPR screens, bulk and single-cell RNA-seq.",
         "tags":["NGS","RNA-seq","CRISPR","Python","Bioinformatics"],
         "url":"https://careers.gene.com/us/en/search-results?keywords=Research+Scientist+Genomics"},
        {"id":"res-us-003","title":"Principal Scientist – Computational Biology",
         "company":"Amgen","location":"Thousand Oaks, CA (Hybrid)",
         "salary_min":155_000,"salary_max":200_000,
         "description":"Lead computational genomics for oncology pipeline. Develop ML models for biomarker discovery. Mentor junior scientists.",
         "tags":["Computational Biology","Machine Learning","R","Python","Genomics"],
         "url":"https://careers.amgen.com/en/search-jobs?keyword=Computational+Biology"},
        {"id":"res-us-004","title":"Staff Scientist – Cell Biology & Imaging",
         "company":"Salk Institute for Biological Studies","location":"La Jolla, CA",
         "salary_min":95_000,"salary_max":130_000,
         "description":"Advanced confocal imaging, flow cytometry, cell culture. Supervise research assistants, contribute to NIH grant writing.",
         "tags":["Cell Biology","Flow Cytometry","Confocal","Grant Writing","IRB"],
         "url":"https://www.salk.edu/about/careers/"},
        {"id":"res-us-005","title":"Senior Research Scientist – RNA Biology",
         "company":"AstraZeneca","location":"Gaithersburg, MD (Hybrid)",
         "salary_min":140_000,"salary_max":175_000,
         "description":"RNA therapeutics platform. Mechanistic studies of RNA processing, splicing, and decay. Lead IND-enabling studies.",
         "tags":["RNA Biology","RNA-seq","CRISPR","Drug Discovery","IND"],
         "url":"https://careers.astrazeneca.com/search-jobs?keywords=Senior+Research+Scientist+RNA"},
        {"id":"res-us-006","title":"Bioinformatics Scientist – NGS Data Analysis",
         "company":"Illumina","location":"San Diego, CA (Hybrid)",
         "salary_min":120_000,"salary_max":155_000,
         "description":"Develop NGS analysis pipelines. Collaborate with product teams on variant calling algorithms. Strong Python/R required.",
         "tags":["Bioinformatics","NGS","Python","R","Variant Calling","Pipeline Development"],
         "url":"https://illumina.wd1.myworkdayjobs.com/illumina-careers?q=Bioinformatics"},
        {"id":"res-us-007","title":"Research Associate III – Molecular Biology",
         "company":"Regeneron","location":"Tarrytown, NY (On-site)",
         "salary_min":75_000,"salary_max":95_000,
         "description":"Support protein expression, western blot, ELISA, PCR. Maintain cell culture facility. Contribute to IND filings.",
         "tags":["Molecular Biology","Western Blot","PCR","Cell Culture","ELISA"],
         "url":"https://regeneron.wd1.myworkdayjobs.com/External?q=Research+Associate+Molecular"},
        {"id":"res-us-008","title":"Director of Research – AI-Assisted Drug Discovery",
         "company":"Recursion Pharmaceuticals","location":"Salt Lake City, UT (Hybrid)",
         "salary_min":175_000,"salary_max":230_000,
         "description":"Lead AI-driven biology research. Bridge wet lab and computational biology. Manage cross-functional team of 15. NIH SBIR experience preferred.",
         "tags":["AI","Drug Discovery","Computational Biology","Leadership","NIH"],
         "url":"https://www.recursion.com/careers?keyword=Director+Research"},
    ]


def _research_jobs_in() -> List[Dict]:
    return [
        {"id":"res-in-001","title":"Research Scientist – Genomics & Bioinformatics",
         "company":"Institute of Genomics and Integrative Biology (IGIB)","location":"Delhi, India",
         "salary_min":1_200_000,"salary_max":2_000_000,
         "description":"RNA-seq, GWAS, population genomics. DBT/DST-funded lab. Opportunity to lead R&D projects and co-author grants.",
         "tags":["Genomics","RNA-seq","Bioinformatics","R","Python","DBT"],
         "url":"https://www.igib.res.in/vacancies"},
        {"id":"res-in-002","title":"Postdoctoral Research Fellow – Cancer Biology",
         "company":"Tata Memorial Centre (TMC)","location":"Mumbai, Maharashtra",
         "salary_min":800_000,"salary_max":1_200_000,
         "description":"Translational cancer research, immunotherapy, CRISPR screens. Collaborate with clinical oncologists. DST-funded position.",
         "tags":["Cancer Biology","CRISPR","Immunotherapy","Translational Research","DST"],
         "url":"https://tmc.gov.in/index.php/recruitments"},
        {"id":"res-in-003","title":"Principal Scientist – Computational Drug Discovery",
         "company":"Dr. Reddy's Laboratories","location":"Hyderabad, Telangana",
         "salary_min":2_500_000,"salary_max":4_000_000,
         "description":"AI/ML for drug target identification. Molecular docking, ADMET prediction. Lead 5-person computational chemistry team.",
         "tags":["Drug Discovery","Machine Learning","Bioinformatics","Python","Leadership"],
         "url":"https://careers.drreddys.com/search/?q=Principal+Scientist+Computational"},
    ]


def _data_science_jobs_us() -> List[Dict]:
    return [
        {"id":"ds-us-001","title":"Senior Data Scientist – NLP & LLM",
         "company":"Meta AI","location":"Menlo Park, CA (Hybrid)",
         "salary_min":200_000,"salary_max":280_000,
         "description":"Large language model fine-tuning, RLHF, evaluation frameworks. PyTorch, Transformers. Lead cross-functional AI projects.",
         "tags":["LLM","NLP","PyTorch","Transformers","RLHF","Python"],
         "url":"https://www.metacareers.com/jobs?q=Senior+Data+Scientist+NLP"},
        {"id":"ds-us-002","title":"ML Engineer – Recommendation Systems",
         "company":"Netflix","location":"Los Gatos, CA (Hybrid)",
         "salary_min":180_000,"salary_max":260_000,
         "description":"Build real-time recommendation models at scale. TensorFlow, Spark, Kubernetes. Feature engineering and A/B testing frameworks.",
         "tags":["Machine Learning","Recommendation Systems","TensorFlow","Spark","A/B Testing"],
         "url":"https://jobs.netflix.com/search?q=ML+Engineer+Recommendation"},
        {"id":"ds-us-003","title":"Applied Scientist – Computer Vision",
         "company":"Amazon","location":"Seattle, WA (Hybrid)",
         "salary_min":175_000,"salary_max":250_000,
         "description":"Deploy CV models in production at Amazon scale. SageMaker, PyTorch, ONNX. Work on real-world customer impact projects.",
         "tags":["Computer Vision","PyTorch","SageMaker","AWS","Production ML"],
         "url":"https://amazon.jobs/en/search?base_query=Applied+Scientist+Computer+Vision"},
        {"id":"ds-us-004","title":"Data Scientist – Healthcare AI",
         "company":"Kaiser Permanente","location":"Pasadena, CA (Hybrid)",
         "salary_min":140_000,"salary_max":185_000,
         "description":"Predictive models for patient outcomes, readmission risk, and clinical decision support. Python, SQL, EHR data.",
         "tags":["Healthcare AI","Python","SQL","Predictive Modeling","EHR","HIPAA"],
         "url":"https://jobs.kp.org/search/?q=Data+Scientist+Healthcare+AI"},
        {"id":"ds-us-005","title":"MLOps Engineer – Model Platform",
         "company":"Uber","location":"San Francisco, CA (Hybrid)",
         "salary_min":165_000,"salary_max":235_000,
         "description":"Build and operate ML platform. MLflow, Kubeflow, feature stores, model registry. SLA 99.99% uptime for production models.",
         "tags":["MLOps","Kubeflow","MLflow","Kubernetes","Feature Store","Platform"],
         "url":"https://www.uber.com/us/en/careers/list/?q=MLOps+Engineer"},
    ]


def _data_science_jobs_in() -> List[Dict]:
    return [
        {"id":"ds-in-001","title":"Senior Data Scientist – Generative AI",
         "company":"Infosys AI Lab","location":"Bangalore, Karnataka",
         "salary_min":2_800_000,"salary_max":4_500_000,
         "description":"LLM fine-tuning, RAG pipelines, enterprise AI products. Python, LangChain, Hugging Face. Lead 4-member team.",
         "tags":["LLM","Generative AI","Python","LangChain","Hugging Face"],
         "url":"https://career.infosys.com/jobdesc.html?keyword=Senior+Data+Scientist+AI"},
        {"id":"ds-in-002","title":"ML Engineer – Recommendation & Personalisation",
         "company":"Flipkart","location":"Bangalore, Karnataka",
         "salary_min":2_500_000,"salary_max":4_000_000,
         "description":"Build recommendation models serving 300M users. TensorFlow, Spark, Feast feature store. Real-time inference at scale.",
         "tags":["Machine Learning","TensorFlow","Spark","Recommendation","Feature Store"],
         "url":"https://www.flipkartcareers.com/#!/joblist?q=ML+Engineer"},
    ]


def _engineering_jobs_us() -> List[Dict]:
    return [
        {"id":"eng-us-001","title":"Senior Software Engineer – Backend (Python/Go)",
         "company":"Stripe","location":"Remote – US",
         "salary_min":180_000,"salary_max":260_000,
         "description":"Build financial infrastructure at scale. Python/Go, distributed systems, high-reliability APIs. Work on core payments platform.",
         "tags":["Python","Go","Distributed Systems","Backend","Payments","High Scale"],
         "url":"https://stripe.com/jobs/search?q=Senior+Software+Engineer+Backend"},
        {"id":"eng-us-002","title":"Staff Engineer – Platform / Kubernetes",
         "company":"Datadog","location":"Remote – US",
         "salary_min":200_000,"salary_max":280_000,
         "description":"Lead platform architecture for 25,000+ customers. Kubernetes, Go, Rust. Design systems handling 100TB+ daily ingest.",
         "tags":["Kubernetes","Go","Rust","Platform Engineering","SRE","Distributed Systems"],
         "url":"https://careers.datadoghq.com/detail/open-positions/?q=Staff+Engineer+Platform"},
        {"id":"eng-us-003","title":"Cloud Engineer – AWS Infrastructure",
         "company":"Airbnb","location":"San Francisco, CA (Hybrid)",
         "salary_min":170_000,"salary_max":240_000,
         "description":"Design and operate AWS infrastructure at scale. Terraform, EKS, RDS, Aurora. Implement cost optimisation and FinOps practices.",
         "tags":["AWS","Terraform","Kubernetes","EKS","FinOps","Cloud Infrastructure"],
         "url":"https://careers.airbnb.com/positions/?q=Cloud+Engineer+AWS"},
    ]


def _healthcare_jobs_us() -> List[Dict]:
    return [
        {"id":"hc-us-001","title":"Healthcare Quality Manager – Patient Safety",
         "company":"Cedars-Sinai Medical Center","location":"Los Angeles, CA",
         "salary_min":95_000,"salary_max":130_000,
         "description":"Lead PDSA improvement cycles, TJC survey readiness, patient safety initiatives. CPHQ preferred. Lean/Six Sigma experience.",
         "tags":["CPHQ","Patient Safety","TJC","Lean","Six Sigma","Quality Improvement"],
         "url":"https://jobs.cedars-sinai.edu/search/?q=Healthcare+Quality+Manager"},
        {"id":"hc-us-002","title":"Clinical Data Analyst – Health Informatics",
         "company":"UCLA Health","location":"Los Angeles, CA (Hybrid)",
         "salary_min":85_000,"salary_max":115_000,
         "description":"Analyse EHR data (Epic) to drive clinical quality reporting. SQL, Tableau, HL7 FHIR. Support population health programs.",
         "tags":["Health Informatics","SQL","Tableau","Epic","FHIR","Population Health"],
         "url":"https://www.uclahealth.org/careers?q=Clinical+Data+Analyst"},
    ]


def _finance_jobs_us() -> List[Dict]:
    return [
        {"id":"fin-us-001","title":"Equity Research Analyst – Technology",
         "company":"Goldman Sachs","location":"New York, NY",
         "salary_min":110_000,"salary_max":160_000,
         "description":"Cover 15–20 large-cap tech stocks. DCF, sum-of-parts valuation, channel checks. CFA candidacy required.",
         "tags":["Equity Research","DCF","Valuation","CFA","Bloomberg","Financial Modeling"],
         "url":"https://www.goldmansachs.com/careers/professionals/search-jobs?q=Equity+Research+Analyst"},
        {"id":"fin-us-002","title":"Risk Manager – Market Risk (FRM)",
         "company":"JPMorgan Chase","location":"New York, NY (Hybrid)",
         "salary_min":130_000,"salary_max":175_000,
         "description":"Market risk VaR monitoring, stress testing, regulatory capital (Basel III). FRM or CFA required. Python/SQL for risk analytics.",
         "tags":["Market Risk","VaR","Basel III","FRM","Python","Stress Testing"],
         "url":"https://jpmc.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1001/requisitions?keyword=Risk+Manager+Market"},
    ]
