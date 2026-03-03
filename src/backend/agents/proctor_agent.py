"""
Proctor Agent — Phase 5 Core Agent (HEAVY tier → Celery queue in v2).

SIMULATION ENGINE:
  Manages stateful proctored exam sessions with adaptive difficulty.
  Session store is in-memory (module-level dict) for v1 stack.
  Redis-backed in v2 (Phase 6 migration).

MODES:
  practice  — 10 questions, immediate per-question feedback, no timer pressure
  exam      — 30 questions, feedback deferred to results, 90-min timer

ADAPTIVE DIFFICULTY:
  Starts at medium. After 3 consecutive correct → upgrades to hard.
  After 3 consecutive wrong → downgrades to easy.
  Exam scores weighted: easy=1pt, medium=2pt, hard=3pt (out of scaled max).

READINESS SCORE:
  Simplified IRT sigmoid: P(pass) = 1 / (1 + exp(−k × (θ − b)))
  θ = estimated ability [-3..+3] from weighted performance
  b = cert-specific difficulty threshold
  Returns 0–100 predicted pass probability.

WEAKNESS TRACKING:
  Per-domain attempt/correct counters persisted to session history.
  Aggregated across all sessions for the user (in-memory per server restart).
  v2: persisted to user.profile_json["weakness_tracker"].

⚠️ CAPACITY FLAG: resource_tier = HEAVY
  Each session creation: <5ms (pure Python).
  Peak: 50 concurrent sessions × 30 questions = 1,500 question records in memory.
  At 1KB/session → 50KB RAM — negligible.
  Migration trigger: sessions > 10,000 concurrent → Redis + session TTL cleanup job.
"""
import logging
import math
import random
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

from .base_agent import AgentResult, BaseAgent, ResourceTier

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────

PRACTICE_Q_COUNT = 10
EXAM_Q_COUNT     = 30
EXAM_TIME_LIMIT  = 90 * 60   # 90 minutes in seconds
SESSION_TTL      = 35 * 60   # 35-minute expiry (5 min grace over exam time)

_DIFFICULTY_UPGRADE_THRESHOLD = 3   # consecutive correct before →hard
_DIFFICULTY_DOWNGRADE_THRESHOLD = 3 # consecutive wrong before →easy

# Cert-specific IRT difficulty (b-parameter) — higher = harder exam
_CERT_DIFFICULTY_THRESHOLD = {
    "aigp":  0.55,   # IAPP AIGP: moderate-hard conceptual
    "cisa":  0.50,   # ISACA CISA: broad coverage, moderate
    "aaia":  0.60,   # AI Audit: emerging, harder threshold
    "ciasp": 0.65,   # CIASP: technical FAIR/risk maths
}

_CERT_PASSING_SCORE = {
    "aigp":  300,   # 300/500 scaled score
    "cisa":  450,   # 450/800 scaled score
    "aaia":  70,    # 70% correct
    "ciasp": 70,    # 70% correct
}

# IRT slope (k-parameter) — steepness of sigmoid curve
_IRT_K = 1.8


# ── In-Memory Session Store ────────────────────────────────────────────────
# {session_id: session_dict}
_SESSIONS: Dict[str, Dict[str, Any]] = {}

# Per-user weakness aggregator (keyed by user_id or email)
# {user_id: {domain_id: {attempts: int, correct: int}}}
_WEAKNESS_STORE: Dict[str, Dict[str, Dict[str, int]]] = {}


# ── Expanded Question Bank ─────────────────────────────────────────────────
# These supplement the Phase 3 artifact_sovereign_agent question bank.
# Combined, they provide ≥30 questions per cert for full exam mode.
# Structure: {text, options[4], correct_index, explanation, distractor_logic, domain, difficulty}

_PROCTOR_QUESTION_BANK: Dict[str, List[Dict[str, Any]]] = {
    "aigp": [
        # ── Domain 1: Foundations ───────────────────────────────────────
        {
            "text": "Which statement BEST describes the difference between narrow AI and general AI?",
            "options": [
                "Narrow AI can only process text; general AI can process images and text simultaneously",
                "Narrow AI is designed for a specific task domain; general AI can perform any intellectual task a human can do",
                "Narrow AI uses machine learning; general AI uses rule-based expert systems",
                "Narrow AI operates offline; general AI requires constant internet connectivity",
            ],
            "correct_index": 1,
            "explanation": "Narrow (weak) AI systems are optimised for specific, bounded tasks — like image recognition or chess — and cannot transfer capabilities to other domains. General AI (AGI) would match or exceed human-level performance across ALL cognitive domains. No production AGI system currently exists; all current AI products are narrow AI.",
            "distractor_logic": "Option A confuses modality with generality — multimodal AI can process text AND images but remains narrow. Option C inverts the relationship — many narrow AI systems use ML, and expert systems are narrow by design. Option D is a network dependency issue, unrelated to the narrow/general distinction.",
            "domain": "aigp_d1",
            "difficulty": "easy",
        },
        {
            "text": "An AI governance framework specifies that all AI models must undergo 'red-teaming' before production deployment. What does red-teaming primarily test?",
            "options": [
                "The model's training data quality and representation balance",
                "The model's adversarial robustness by simulating attacks and misuse scenarios",
                "The model's computational efficiency and inference latency under load",
                "The model's alignment with the organisation's brand voice and tone guidelines",
            ],
            "correct_index": 1,
            "explanation": "Red-teaming in AI governance involves structured adversarial testing where designated testers actively try to make the model produce harmful, biased, or unintended outputs. This includes prompt injection, jailbreaking, role-playing attacks, and misinformation elicitation. It directly tests safety, harm resistance, and policy compliance — not technical performance.",
            "distractor_logic": "Option A describes data auditing, a separate process. Option C describes load/performance testing. Option D describes brand alignment — relevant but handled by separate content guidelines review, not red-teaming.",
            "domain": "aigp_d1",
            "difficulty": "medium",
        },
        # ── Domain 2: Risk Management ────────────────────────────────────
        {
            "text": "During an AI risk assessment, which risk taxonomy maps MOST directly to the NIST AI RMF MAP function's output?",
            "options": [
                "A quantitative FAIR model computing annual loss expectancy for each AI system",
                "A risk register cataloguing identified AI risks with likelihood, impact, and ownership",
                "A compliance checklist verifying EU AI Act Article requirements",
                "A vulnerability scan report from an automated security assessment tool",
            ],
            "correct_index": 1,
            "explanation": "The NIST AI RMF MAP function produces a contextualised risk register — it identifies what can go wrong with the AI system in its specific deployment context, who is impacted, and who owns the risk. The FAIR model (A) is quantitative and belongs to MEASURE. A compliance checklist (C) is used in GOVERN/MANAGE. A vulnerability scan (D) is a cybersecurity tool, not an AI risk taxonomy.",
            "distractor_logic": "The FAIR model IS used in AI risk management but it's a MEASURE function tool — it quantifies risks already identified in MAP. The compliance checklist supports GOVERN (policy) and MANAGE (remediation). Vulnerability scans find software flaws, not AI-specific risks like bias, hallucination, or misuse.",
            "domain": "aigp_d2",
            "difficulty": "hard",
        },
        {
            "text": "Which AI risk category is MOST difficult to detect through pre-deployment testing alone?",
            "options": [
                "Training data quality defects causing systematic output errors",
                "Model hallucination producing confident but factually incorrect outputs",
                "Distribution shift causing performance degradation when real-world data diverges from training data over time",
                "Adversarial inputs triggering misclassification through malicious perturbations",
            ],
            "correct_index": 2,
            "explanation": "Distribution shift (concept drift / data drift) occurs when real-world data distributions change AFTER deployment — the model's training data becomes unrepresentative. This CANNOT be detected pre-deployment because the future data doesn't exist yet. Pre-deployment testing can detect training data defects (A), hallucination patterns (B), and adversarial vulnerabilities (D).",
            "distractor_logic": "All other options can be systematically tested before deployment. Hallucination can be evaluated on held-out test sets. Adversarial robustness uses red-team testing. Only distribution shift requires continuous post-deployment monitoring because it's caused by the world changing, not the model.",
            "domain": "aigp_d2",
            "difficulty": "hard",
        },
        # ── Domain 3: Fairness / XAI ─────────────────────────────────────
        {
            "text": "A model achieves 95% accuracy on the majority class and 40% accuracy on the minority class. Which fairness problem does this BEST illustrate?",
            "options": [
                "Demographic parity — the model predicts positive outcomes at different rates for different groups",
                "Disparate impact — overall accuracy is fine but subgroup accuracy is severely imbalanced",
                "Calibration error — predicted probabilities don't match actual outcomes",
                "Individual fairness — similar individuals are treated differently by the model",
            ],
            "correct_index": 1,
            "explanation": "Disparate impact occurs when a seemingly neutral metric (like overall accuracy) masks severe performance differences across subgroups. A model with 95%/40% accuracy across majority/minority classes has WORSE predictive value for the minority class — a classic disparate impact finding. Regulators (CFPB, EEOC) specifically look for this pattern when evaluating algorithmic discrimination.",
            "distractor_logic": "Demographic parity concerns prediction RATES (what % are predicted positive), not accuracy. Calibration concerns whether probabilities are well-estimated. Individual fairness requires comparing specific pairs of similar individuals. The described scenario is specifically a subgroup accuracy disparity.",
            "domain": "aigp_d3",
            "difficulty": "medium",
        },
        {
            "text": "Under GDPR Article 22, what is an individual's right regarding automated decision-making?",
            "options": [
                "The right to opt out of any AI system that processes their data",
                "The right not to be subject to decisions based solely on automated processing that produce legal or similarly significant effects, without human involvement",
                "The right to receive a full technical explanation of the AI model's architecture",
                "The right to have their data removed from the AI training dataset",
            ],
            "correct_index": 1,
            "explanation": "GDPR Article 22 grants individuals the right not to be subject to SOLELY automated decisions (no meaningful human involvement) that produce legal effects (e.g., loan denial, employment rejection) or similarly significant effects. Organisations must either obtain explicit consent, show necessity for contract performance, or have EU/member state legal authorisation — and must provide human review on request.",
            "distractor_logic": "Option A is too broad — Article 22 doesn't require opt-out of all AI, only solely automated significant decisions. Option C: the right to explanation (Article 13/14/15) requires 'meaningful information about the logic involved' — not full technical disclosure. Option D is the right to erasure (Article 17) — a separate provision.",
            "domain": "aigp_d3",
            "difficulty": "medium",
        },
        # ── Domain 4: Governance Maturity ────────────────────────────────
        {
            "text": "Which role in an AI governance structure is PRIMARILY responsible for ensuring AI systems comply with applicable laws and regulations?",
            "options": [
                "Chief AI Officer (CAIO) — sets AI strategy and investment priorities",
                "AI Ethics Board — reviews AI decisions for moral alignment",
                "Chief Compliance Officer (CCO) / AI Legal Counsel — ensures regulatory adherence",
                "Data Steward — maintains data quality and lineage records",
            ],
            "correct_index": 2,
            "explanation": "Regulatory compliance accountability sits with the CCO and legal counsel, who map AI activities to applicable laws (EU AI Act, CCPA, HIPAA, EEOC, etc.), manage regulatory filings, and advise on compliance gaps. The CAIO drives strategy. The Ethics Board advises on values-based decisions. The Data Steward manages data assets. Compliance with laws is a legal/compliance function.",
            "distractor_logic": "The CAIO is accountable for AI strategy alignment with business goals, not legal compliance. The Ethics Board (where it exists) addresses ethical principles — a higher-order concern than legal minimum compliance. Data Stewards manage data governance, not regulatory AI requirements.",
            "domain": "aigp_d4",
            "difficulty": "easy",
        },
        {
            "text": "An AI governance programme wants to implement a 'Model Risk Management' (MRM) framework similar to SR 11-7 (Federal Reserve). What is the FIRST step?",
            "options": [
                "Define model validation standards and testing protocols",
                "Establish a model inventory cataloguing all AI/ML models in use",
                "Hire a dedicated Chief Model Risk Officer",
                "Implement an automated model monitoring platform",
            ],
            "correct_index": 1,
            "explanation": "SR 11-7 guidance requires a complete model inventory as the foundational step — you cannot govern, validate, or monitor models you don't know exist. The inventory records model purpose, owner, data inputs, outputs, and materiality. Without it, the governance programme has unknown blind spots. Validation standards, CMRO, and monitoring all depend on knowing which models exist.",
            "distractor_logic": "Validation standards (A) require knowing what to validate — impossible without inventory. Hiring a CMRO (C) is an org design step that can happen in parallel but the inventory is operationally first. Monitoring (D) requires models to be already catalogued and governed.",
            "domain": "aigp_d4",
            "difficulty": "medium",
        },
        # ── Domain 5: Regulatory ─────────────────────────────────────────
        {
            "text": "Under the EU AI Act, which type of AI system requires a conformity assessment by a notified body (third-party) rather than a self-assessment?",
            "options": [
                "All high-risk AI systems in any sector",
                "High-risk AI systems used in biometric identification and categorisation",
                "High-risk AI systems used in education, employment, and essential services — if not covered by existing EU law",
                "Limited-risk AI systems that interact with humans (chatbots)",
            ],
            "correct_index": 1,
            "explanation": "EU AI Act Article 43 requires third-party conformity assessment (by a notified body) specifically for high-risk AI systems involving biometric identification/categorisation — due to their significant impact on fundamental rights. Most other high-risk AI systems allow self-assessment against harmonised standards. Chatbots (limited risk) only have transparency obligations — no conformity assessment.",
            "distractor_logic": "Option A overstates the requirement — most high-risk systems can self-assess if complying with harmonised standards. Option C is a category that allows self-assessment. Option D (chatbots) requires transparency disclosure, not conformity assessment. Biometric systems are singled out for stricter oversight.",
            "domain": "aigp_d5",
            "difficulty": "hard",
        },
        {
            "text": "Which of the following would qualify as a 'general-purpose AI model' (GPAI) under the EU AI Act?",
            "options": [
                "A customer service chatbot trained specifically for a bank's FAQ",
                "A large language model capable of generating text, code, images, and performing reasoning across domains",
                "A computer vision system trained to detect defects on a manufacturing assembly line",
                "A recommendation engine trained on a streaming platform's viewing history",
            ],
            "correct_index": 1,
            "explanation": "EU AI Act Article 3(63) defines general-purpose AI models as AI models trained on large datasets, designed to perform a wide range of distinct tasks, and capable of integration into various downstream systems. A large language model (GPT-4, Claude, Gemini) clearly meets this definition. The bank chatbot, vision system, and recommender are all single-purpose narrow systems.",
            "distractor_logic": "Options A, C, D are all narrow, task-specific systems trained for a single application domain. A GPAI model must be capable of competent performance across multiple distinct domains without task-specific retraining.",
            "domain": "aigp_d5",
            "difficulty": "medium",
        },
        # ── Domain 6: Assurance ──────────────────────────────────────────
        {
            "text": "When auditing an AI system's training process, which control provides the STRONGEST evidence that the training data was free from prohibited personal data?",
            "options": [
                "The data provider's contract warranty excluding personal data",
                "Automated data pipeline logs showing PII scrubbing scripts executed on each batch",
                "A privacy impact assessment completed before training commenced",
                "The model's inability to reproduce training data verbatim in output testing",
            ],
            "correct_index": 1,
            "explanation": "Automated pipeline logs showing PII scrubbing scripts executed on each training batch provide direct, primary evidence of the control operating effectively. This is operational evidence — the auditor can verify timestamps, script execution logs, and exception records. The contract warranty (A) is a legal protection, not evidence of PII absence. The PIA (C) is planning-stage evidence. Output testing (D) tests for memorisation, not upstream data cleansing.",
            "distractor_logic": "Contract warranties shift liability but don't prove compliance. PIAs document intent, not execution. Output testing is a useful secondary test but doesn't prove the pipeline control operated. Log evidence of automated PII scrubbing is the most direct evidence of the control itself.",
            "domain": "aigp_d6",
            "difficulty": "hard",
        },
        {
            "text": "An AI auditor is reviewing the organisation's 'acceptable use policy' for generative AI tools. Which element is MOST critical from a data governance perspective?",
            "options": [
                "A list of approved generative AI tools and prohibited competitors' tools",
                "A prohibition on inputting confidential, proprietary, or personal data into non-enterprise AI tools",
                "A requirement for employees to disclose AI-generated content in all external communications",
                "A training programme on effective prompt engineering techniques",
            ],
            "correct_index": 1,
            "explanation": "From a data governance perspective, the most critical element is preventing employees from inadvertently exfiltrating confidential data (trade secrets, PII, financial data) to consumer AI tools where data may be used for model training or accessed by the vendor. This addresses the highest-impact data risk. Approved tool lists (A) are important but incomplete without data handling rules. Disclosure (C) and prompt training (D) are compliance and operational elements.",
            "distractor_logic": "Tool approval lists without data restrictions can still result in data exposure via approved tools. Disclosure requirements address transparency obligations, not data protection. Prompt training improves outputs but doesn't address data governance risk.",
            "domain": "aigp_d6",
            "difficulty": "medium",
        },
    ],

    "cisa": [
        # ── Domain 1: Audit Process ──────────────────────────────────────
        {
            "text": "An IS auditor is assessing the risk of undetected errors in an organisation's financial reporting system. Which audit technique provides the MOST direct evidence of control effectiveness?",
            "options": [
                "Interviewing control owners about their control procedures",
                "Reviewing policy documentation and procedure manuals",
                "Re-performing a sample of control operations and comparing results",
                "Observing a control operation once during a walkthrough",
            ],
            "correct_index": 2,
            "explanation": "Re-performance is the highest-assurance audit technique — the auditor independently repeats the control (e.g., recalculates a reconciliation, retests an access approval) and compares the result to the documented output. This provides direct evidence that the control is operating effectively, not just documented or described. Observation and interviews provide weaker evidence as they are one-time and self-reported, respectively.",
            "distractor_logic": "Interviews (A) provide enquiry evidence — the weakest form. Documentation review (B) tests design, not operation. Observation (C) is one-time and may reflect 'Hawthorne effect' — staff behave differently when watched. Only re-performance provides independently produced evidence of control operation.",
            "domain": "cisa_d1",
            "difficulty": "medium",
        },
        {
            "text": "During an IS audit, an auditor identifies a significant finding after the initial report has been distributed. What is the CORRECT course of action?",
            "options": [
                "Issue an addendum to the original report documenting the new finding",
                "Discard the finding since the audit period has closed",
                "Report the finding verbally to management only",
                "Wait and include the finding in the next scheduled audit",
            ],
            "correct_index": 0,
            "explanation": "ISACA auditing standards require that significant findings be communicated even if discovered post-distribution. The correct action is to issue a formal addendum (or supplemental report) to the original audit report, documenting the finding with the same rigour as the original. This preserves the audit trail and ensures management accountability.",
            "distractor_logic": "Discarding (B) violates auditor objectivity and due professional care. Verbal-only reporting (C) lacks documentation and is not auditable. Deferring to the next audit (D) leaves management without timely information on a significant issue. The addendum approach maintains completeness of the record.",
            "domain": "cisa_d1",
            "difficulty": "easy",
        },
        {
            "text": "An IS auditor using Computer-Assisted Audit Techniques (CAATs) wants to test 100% of transactions for duplicate payments. Which CAAT category is being used?",
            "options": [
                "Embedded audit modules that monitor transactions in real time",
                "Integrated Test Facility (ITF) that introduces test records into production",
                "Data extraction and analysis tools that query transaction history",
                "Parallel simulation that re-processes transactions with audit software",
            ],
            "correct_index": 2,
            "explanation": "Data extraction and analysis (using tools like ACL/Galvanize, IDEA, or SQL queries) allows auditors to extract 100% of transactions and run automated duplicate detection tests — matching on vendor, amount, date, and payment reference. This is the most common CAAT for completeness testing. Embedded modules (A) require advance implementation. ITF (B) tests future transactions. Parallel simulation (C) re-processes rather than queries history.",
            "distractor_logic": "Embedded audit modules require pre-planned placement in the production system — they can't be added post-hoc for historical testing. ITF introduces fictitious test data and validates system processing logic, not historical completeness. Parallel simulation verifies processing accuracy by re-running transactions.",
            "domain": "cisa_d1",
            "difficulty": "medium",
        },
        # ── Domain 2: IT Governance ───────────────────────────────────────
        {
            "text": "Which IT governance framework specifically addresses the alignment of IT with business objectives through five key domains: Evaluate, Direct and Monitor?",
            "options": [
                "ITIL v4 — IT Infrastructure Library service value system",
                "COBIT 2019 — Control Objectives for Information and Related Technologies",
                "ISO 27001 — Information Security Management System",
                "NIST CSF — Cybersecurity Framework",
            ],
            "correct_index": 1,
            "explanation": "COBIT 2019 (formerly COBIT 5) uses the EDM (Evaluate, Direct, Monitor) governance domain as its IT governance framework, specifically designed to align IT with business objectives, enable value delivery, and manage risk. ITIL focuses on service management. ISO 27001 focuses on information security. NIST CSF focuses on cybersecurity resilience.",
            "distractor_logic": "ITIL's service value system optimises service delivery, not business-IT alignment governance. ISO 27001 certifies information security management. NIST CSF (Identify/Protect/Detect/Respond/Recover) addresses cybersecurity risk, not IT governance broadly.",
            "domain": "cisa_d2",
            "difficulty": "easy",
        },
        {
            "text": "An IS auditor finds that IT project governance lacks a formal project portfolio management process. What is the PRIMARY risk of this gap?",
            "options": [
                "Individual projects may run over budget and schedule",
                "The organisation may invest in projects that don't align with strategic priorities or that compete for the same scarce resources",
                "Technical debt accumulates in legacy systems",
                "Vendor contracts for project tools may not be renewed",
            ],
            "correct_index": 1,
            "explanation": "Without portfolio management, the organisation lacks a mechanism to evaluate, prioritise, and balance IT investments against strategic objectives and resource constraints. This leads to strategic misalignment — funding low-priority projects while high-priority strategic initiatives are underfunded — and resource conflicts. Individual project overruns (A) are a symptom of project management gaps, not portfolio governance.",
            "distractor_logic": "Option A (budget/schedule overruns) is a project management risk, not a portfolio risk. Technical debt (C) is a technical architecture concern. Vendor contracts (D) are a procurement issue unrelated to portfolio governance.",
            "domain": "cisa_d2",
            "difficulty": "medium",
        },
        # ── Domain 3: Systems Acquisition ────────────────────────────────
        {
            "text": "During the system acquisition phase, which activity provides ISACA-recommended assurance that the purchased software meets security requirements?",
            "options": [
                "Vendor due diligence questionnaire on the vendor's security posture",
                "Security testing (VAPT) of the software in a staging environment mirroring production",
                "Contractual warranty by the vendor that the software is free from vulnerabilities",
                "Review of the software's SOC 2 Type I report",
            ],
            "correct_index": 1,
            "explanation": "Vulnerability Assessment and Penetration Testing (VAPT) of the software in a staging environment provides direct evidence of security posture before go-live. This is primary evidence obtained by the organisation. Vendor questionnaires and warranties are self-reported and legally limited. A SOC 2 Type I reports on controls AT A POINT IN TIME — Type II over a period is more useful, but neither substitutes for environment-specific testing.",
            "distractor_logic": "Vendor questionnaires are self-assessments with no independent validation. Contractual warranties shift liability but don't prevent breaches. SOC 2 Type I confirms design only, not operating effectiveness; and covers the vendor's own environment, not your specific deployment configuration.",
            "domain": "cisa_d3",
            "difficulty": "medium",
        },
        # ── Domain 4: IT Operations ───────────────────────────────────────
        {
            "text": "A company's RTO for its core ERP system is 4 hours. During a tabletop DR exercise, the IT team estimates it takes 6 hours to restore the system from cold backup. What should the auditor conclude?",
            "options": [
                "The DR plan is adequate — the 2-hour gap is within acceptable tolerance",
                "The DR plan has an RTO gap and requires remediation, such as a warm/hot standby configuration",
                "The RTO should be extended to 6 hours to match the actual recovery time",
                "The tabletop exercise is insufficient; a live DR failover test is required to validate the RTO",
            ],
            "correct_index": 1,
            "explanation": "When actual recovery time (6 hours) exceeds the business-defined RTO (4 hours), there is a DR gap — the technical capability does not meet the business requirement. The auditor should flag this as a finding requiring remediation, such as implementing a warm standby (shorter switchover time) or hot standby (near-instant failover). Extending the RTO (C) requires business approval and may be unacceptable. A live test (D) is valuable but doesn't change the current gap finding.",
            "distractor_logic": "Option A: there is no 'acceptable tolerance' — the business set 4 hours based on financial and operational impact. A 50% overage is a significant finding. Option C inverts the accountability — IT must meet business requirements, not the reverse. Option D: while a live test validates recovery procedures, the analytical finding (6h > 4h RTO) is clear from the tabletop.",
            "domain": "cisa_d4",
            "difficulty": "medium",
        },
        {
            "text": "An IS auditor is reviewing change management controls. Which evidence MOST effectively demonstrates that changes were authorised before implementation?",
            "options": [
                "A change log showing the date and time each change was made to production",
                "Completed change request forms with manager approval signatures dated BEFORE the change implementation date",
                "A post-implementation review showing the change achieved its objectives",
                "Incident tickets showing no production issues in the week following the change",
            ],
            "correct_index": 1,
            "explanation": "Change authorisation controls require evidence that approval was obtained PRIOR TO implementation. Completed change request forms with dated manager approvals (before the implementation date) provide direct evidence of the authorisation control. A change log (A) records what happened — not that it was authorised beforehand. Post-implementation reviews (C) and incident metrics (D) assess outcomes, not authorisation.",
            "distractor_logic": "The change log records execution, not authorisation — an unauthorised change would still appear in the log. Post-implementation reviews occur after the fact. Clean incident logs don't prove the change was authorised — it could have gone wrong and been covered up. Only pre-dated approvals prove prior authorisation.",
            "domain": "cisa_d4",
            "difficulty": "easy",
        },
        # ── Domain 5: Protection ─────────────────────────────────────────
        {
            "text": "An IS auditor is reviewing privileged access management (PAM). Which control provides the STRONGEST assurance that privileged accounts are used appropriately?",
            "options": [
                "Requiring a business justification when privileged accounts are provisioned",
                "Implementing multi-factor authentication for all privileged account logins",
                "Recording and archiving full session logs for all privileged account activities, with regular review",
                "Rotating privileged account passwords quarterly",
            ],
            "correct_index": 2,
            "explanation": "Full session recording (keystroke logging, screen capture) with regular human review provides the strongest ongoing assurance of appropriate use — it creates an irrefutable audit trail of what privileged users actually did. Provisioning justification (A) is a one-time control at account creation. MFA (B) controls access but not what happens after login. Password rotation (D) prevents credential reuse but doesn't monitor activity.",
            "distractor_logic": "Justification at provisioning is a preventive control at point-of-access but doesn't detect misuse post-provision. MFA is an authentication control that doesn't monitor what authenticated users do. Password rotation prevents stale credential exploitation but a legitimate user with rotating credentials can still abuse access. Session recording + review is the detective control that provides ongoing behavioural assurance.",
            "domain": "cisa_d5",
            "difficulty": "hard",
        },
        {
            "text": "Which encryption approach provides confidentiality for data in transit between a web browser and a web server?",
            "options": [
                "AES-256 encryption of database records at rest",
                "TLS 1.3 (Transport Layer Security) establishing an encrypted channel",
                "Hashing passwords with bcrypt before storing in the database",
                "Data masking replacing sensitive fields with tokenised values in API responses",
            ],
            "correct_index": 1,
            "explanation": "TLS (Transport Layer Security) specifically addresses data in transit — it establishes a cryptographically authenticated, encrypted channel between the browser and server, protecting against eavesdropping and man-in-the-middle attacks. AES-256 (A) protects data at rest. Bcrypt (C) is a one-way hash for password storage. Data masking/tokenisation (D) reduces the sensitivity of data returned, but doesn't encrypt the transit channel.",
            "distractor_logic": "AES-256 database encryption protects data stored on disk from unauthorised file access — not relevant to transit. Bcrypt hashing protects passwords IF the database is compromised. Tokenisation reduces sensitive data exposure in API responses but doesn't prevent eavesdropping on the unencrypted transport layer.",
            "domain": "cisa_d5",
            "difficulty": "easy",
        },
    ],

    "aaia": [
        # ── Domain 1: MLOps & AI Systems ─────────────────────────────────
        {
            "text": "An AI auditor finds that a production ML model has no documented data lineage. What is the PRIMARY governance risk?",
            "options": [
                "The model may be slower than optimally possible due to unoptimised data pipelines",
                "The organisation cannot trace model outputs back to source data, preventing bias investigation, regulatory compliance, and root cause analysis",
                "Regulatory authorities may require the model to be retrained on approved datasets",
                "The model's intellectual property may be infringed if training sources are unknown",
            ],
            "correct_index": 1,
            "explanation": "Data lineage documents the full journey of data — from source through transformations to training dataset. Without it, the organisation cannot: (1) investigate discriminatory outputs (can't identify if biased data was used), (2) comply with GDPR data source obligations, (3) perform root cause analysis when the model fails. This is the primary governance risk — loss of traceability and accountability.",
            "distractor_logic": "Performance optimisation (A) is a separate technical concern. Mandatory retraining (C) is a potential regulatory consequence, not the primary risk itself. IP infringement (D) is a legal concern but secondary to the governance traceability gap.",
            "domain": "aaia_d1",
            "difficulty": "medium",
        },
        {
            "text": "In an MLOps pipeline, what is the PRIMARY purpose of a 'model registry'?",
            "options": [
                "To store model training data and feature engineering pipelines",
                "To provide a versioned, governed repository for model artifacts with approval workflows and deployment history",
                "To monitor model performance metrics in real-time production environments",
                "To document business requirements and success criteria for AI projects",
            ],
            "correct_index": 1,
            "explanation": "A model registry (e.g., MLflow, Sagemaker Model Registry) is a centralised store for model artifacts (serialised models, metadata, metrics) with version control, stage transitions (Staging→Production), and approval workflows. It enables rollback, audit trail of promotions, and governance of which model version is in production. It is NOT the training data store (A), the monitoring platform (C), or requirements documentation (D).",
            "distractor_logic": "Training data belongs in a data lake or feature store, not the model registry. Real-time monitoring is provided by ML observability platforms. Business requirements live in project management or governance documents. The registry specifically manages model artifacts and their lifecycle states.",
            "domain": "aaia_d1",
            "difficulty": "easy",
        },
        {
            "text": "An AI auditor is reviewing model documentation for a fraud detection model. Which document provides the MOST comprehensive overview of the model's intended use, limitations, and performance across subgroups?",
            "options": [
                "The model's API technical specification document",
                "The vendor's data processing agreement",
                "The model card, following Google's model cards for model reporting standard",
                "The system design document describing the ML architecture",
            ],
            "correct_index": 2,
            "explanation": "Model cards (Mitchell et al., Google, 2019) are the standard documentation format for AI model transparency — they capture: intended use, out-of-scope uses, training data details, performance metrics across demographic subgroups, ethical considerations, and limitations. This is exactly what an AI auditor needs to assess fitness for purpose and subgroup fairness.",
            "distractor_logic": "API specs describe input/output formats for integration, not model behaviour or fairness. Data processing agreements are legal contracts for data handling, not model documentation. System design documents describe architecture and technical implementation, not performance characteristics or ethical considerations.",
            "domain": "aaia_d1",
            "difficulty": "easy",
        },
        # ── Domain 2: AI Audit Methodology ───────────────────────────────
        {
            "text": "When auditing an AI system that makes credit decisions, which regulatory standard SPECIFICALLY requires the organisation to provide adverse action notices with 'specific reasons' for denial?",
            "options": [
                "EU AI Act Article 52 — transparency obligations for AI systems",
                "Equal Credit Opportunity Act (ECOA) / Regulation B — adverse action notice requirements",
                "GDPR Article 22 — automated decision-making rights",
                "NIST AI RMF MANAGE function — risk mitigation requirements",
            ],
            "correct_index": 1,
            "explanation": "The US Equal Credit Opportunity Act (ECOA), implemented by the CFPB's Regulation B, specifically requires creditors to provide adverse action notices listing the 'specific reasons' for credit denial. In the AI context, this creates an 'explainability by regulation' requirement — the AI model must produce specific, actionable reasons (not just a score). The CFPB has clarified this applies to complex model outputs.",
            "distractor_logic": "EU AI Act Article 52 requires transparency disclosures for certain AI systems but is EU-specific and applies differently. GDPR Article 22 applies to EU data subjects. NIST CSF is a voluntary framework. ECOA/Reg B is the specific US regulation requiring specific denial reasons in credit.",
            "domain": "aaia_d2",
            "difficulty": "hard",
        },
        {
            "text": "During an AI audit engagement, what does 'testing for proxy discrimination' refer to?",
            "options": [
                "Testing whether the model uses legally protected attributes (race, gender) as direct inputs",
                "Testing whether facially neutral model features act as proxies for protected characteristics, producing discriminatory outcomes",
                "Testing whether the model's training data was collected with informed consent",
                "Testing whether the model's outputs can be proxied by a simpler, more explainable model",
            ],
            "correct_index": 1,
            "explanation": "Proxy discrimination occurs when a model excludes protected attributes (race, gender) as direct inputs but uses highly correlated proxy variables (ZIP code, school attended) that produce equivalent discriminatory outcomes. Testing for proxy discrimination involves: (1) correlation analysis between features and protected attributes, (2) disparate impact analysis on outputs, (3) sensitivity analysis removing suspected proxies. Removing protected attributes from inputs alone does NOT prevent proxy discrimination.",
            "distractor_logic": "Option A describes direct attribute testing — a simpler but insufficient test. If protected attributes are removed but their proxies remain, discrimination persists. Option C is data privacy testing. Option D describes model compression/distillation — a technical approach unrelated to discrimination testing.",
            "domain": "aaia_d2",
            "difficulty": "hard",
        },
        {
            "text": "An organisation deploys a generative AI customer service agent. Which AI audit control is MOST important to verify first?",
            "options": [
                "Content filtering to prevent the model from generating harmful or off-brand responses",
                "Response latency SLAs and uptime guarantees",
                "Integration testing with the CRM system",
                "Model license compliance and intellectual property clearance",
            ],
            "correct_index": 0,
            "explanation": "For a customer-facing generative AI system, content filtering (output safety controls) is the highest-priority control to verify — a single harmful, biased, or off-brand response can damage brand reputation, violate regulations, or harm customers. This includes: toxicity filtering, hallucination guards, PII detection, and topic restriction. Latency SLAs, CRM integration, and IP compliance are important but secondary to output safety.",
            "distractor_logic": "Latency and uptime are operational KPIs, not safety controls. CRM integration is a functional requirement. IP compliance is legal due diligence. None of these prevent the model from producing harmful outputs to real customers — which is the primary risk of a generative AI deployment.",
            "domain": "aaia_d2",
            "difficulty": "medium",
        },
        {
            "text": "In an AI assurance engagement, what is 'explainability by design' and why is it preferable to post-hoc explanation methods?",
            "options": [
                "Building XAI dashboards into the production system from day one, so explanations are available before go-live",
                "Using inherently interpretable models (decision trees, logistic regression) whose logic is directly readable, rather than approximating complex model behaviour post-hoc",
                "Requiring developers to document their code thoroughly so the model logic can be understood by reviewers",
                "Publishing the model's source code and training data for external researchers to analyse",
            ],
            "correct_index": 1,
            "explanation": "Explainability by design means choosing inherently interpretable model architectures — decision trees, linear regression, rule-based systems — whose logic is directly readable without approximation. Post-hoc methods (SHAP, LIME) approximate a complex black-box model's behaviour for specific instances. This approximation introduces error: SHAP values may not perfectly represent the model's actual decision process. For high-stakes decisions, faithfulness to the actual model logic (only achievable with interpretable models) is superior.",
            "distractor_logic": "Option A describes a deployment timeline for XAI tools, not model architecture choice. Option C describes code documentation, not model interpretability. Option D describes open-sourcing, which enables external review but doesn't make black-box models interpretable.",
            "domain": "aaia_d2",
            "difficulty": "hard",
        },
        {
            "text": "Which sampling strategy is MOST appropriate when auditing an AI model's fairness across a very large dataset (500M rows) where protected attribute labels are present for only 2% of records?",
            "options": [
                "Simple random sampling — take 1% of all records for analysis",
                "Stratified sampling — oversample the 2% labelled records to ensure adequate subgroup representation",
                "Cluster sampling — randomly select geographic regions and test all records in each region",
                "Systematic sampling — test every 100th record in the dataset",
            ],
            "correct_index": 1,
            "explanation": "When the subgroup of interest (labelled records with protected attribute data) represents only 2% of the population, simple random sampling would undersample this group severely — a 1% sample of 500M = 5M records, of which only 2% (100K) have labels, potentially too few for statistically reliable subgroup analysis. Stratified sampling with oversampling of the labelled 2% ensures sufficient labelled records for meaningful fairness metrics.",
            "distractor_logic": "Simple random sampling proportionally represents the full population but severely undersamples the rare labelled subgroup. Cluster sampling groups by geography — if biased patterns aren't geographically clustered, this misses them. Systematic sampling (every 100th) is efficient but has the same subgroup representation problem as simple random.",
            "domain": "aaia_d2",
            "difficulty": "hard",
        },
    ],

    "ciasp": [
        # ── Domain 1: FAIR & Risk Quantification ─────────────────────────
        {
            "text": "In the FAIR model, what is the 'Threat Capability' component and how does it interact with 'Control Strength' to determine vulnerability?",
            "options": [
                "Threat Capability is the frequency of threat events; it divides Control Strength to produce ALE",
                "Threat Capability measures how skilled or resourced a threat actor is; when it exceeds Control Strength, the probability of successful exploit (vulnerability) increases",
                "Threat Capability is the monetary value a threat actor targets; it multiplies primary loss to produce SLE",
                "Threat Capability is synonymous with Threat Event Frequency (TEF) in the FAIR model",
            ],
            "correct_index": 1,
            "explanation": "In FAIR's decomposition, Vulnerability = f(Threat Capability, Control Strength). When a threat actor's capability (skills, resources, persistence) exceeds the organisation's control strength (resistance level), the probability of successful compromise increases. High Threat Capability + Low Control Strength → High Vulnerability. This is distinct from TEF (how often threats occur) and affects the loss event frequency.",
            "distractor_logic": "TEF is a separate FAIR input measuring frequency of threat events — not capability. The monetary target relates to Loss Magnitude, not Threat Capability. Threat Capability specifically measures the QUALITY (skill/resources) of the threat actor relative to the organisation's defences.",
            "domain": "ciasp_d1",
            "difficulty": "hard",
        },
        {
            "text": "An organisation has three security controls: Control A costs $100K/year and reduces ALE by $400K. Control B costs $50K/year and reduces ALE by $60K. Control C costs $200K/year and reduces ALE by $180K. Which decision framework should the CISO apply?",
            "options": [
                "Implement all three controls since all reduce ALE",
                "Implement only Control A — highest absolute ALE reduction",
                "Implement Control A only — positive ROSI (Return on Security Investment) = $300K; B and C have negative ROSI",
                "Implement Controls A and B — both have positive ROSI; C has negative ROSI",
            ],
            "correct_index": 3,
            "explanation": "ROSI = ALE Reduction − Control Cost. Control A: $400K − $100K = +$300K (positive). Control B: $60K − $50K = +$10K (positive). Control C: $180K − $200K = −$20K (negative). Both A and B have positive ROSI — they provide more value than they cost. C costs more than it saves. The rational decision is to implement A and B, not C. This is the fundamental risk-cost optimisation decision in security economics.",
            "distractor_logic": "Option A ignores the cost efficiency of each control — C has negative ROSI and destroys value. Option B picks the highest absolute reduction but ignores that B also has positive ROSI and is cost-efficient. Only Option D correctly applies the ROSI filter: positive ROSI → implement, negative ROSI → decline.",
            "domain": "ciasp_d1",
            "difficulty": "hard",
        },
        {
            "text": "Under the FAIR model, which scenario would produce the HIGHEST Annualised Loss Expectancy (ALE)?",
            "options": [
                "TEF = 1, Vulnerability = 0.9, Primary Loss = $5,000,000",
                "TEF = 10, Vulnerability = 0.5, Primary Loss = $500,000",
                "TEF = 100, Vulnerability = 0.1, Primary Loss = $200,000",
                "TEF = 2, Vulnerability = 0.8, Primary Loss = $3,000,000",
            ],
            "correct_index": 3,
            "explanation": "ALE = TEF × Vulnerability × Primary Loss. Computing each: A = 1×0.9×5,000,000 = $4,500,000. B = 10×0.5×500,000 = $2,500,000. C = 100×0.1×200,000 = $2,000,000. D = 2×0.8×3,000,000 = $4,800,000. Option D produces the highest ALE at $4,800,000, narrowly beating A ($4,500,000). This tests the candidate's ability to apply all three FAIR factors simultaneously.",
            "distractor_logic": "Option A is a tempting answer due to the large $5M loss magnitude. Option C demonstrates that high TEF doesn't automatically mean high ALE if vulnerability and loss magnitude are low. Option B is the mid-range result. Candidates who focus on only one FAIR factor (e.g., highest loss or highest TEF) will choose incorrect answers.",
            "domain": "ciasp_d1",
            "difficulty": "hard",
        },
        {
            "text": "A security analyst is asked to communicate cyber risk to the Board. Which format BEST aligns with FAIR-based risk quantification for executive communication?",
            "options": [
                "A heat map showing red/amber/green risk ratings for each threat scenario",
                "A technical vulnerability report listing CVE scores and affected systems",
                "A probabilistic loss distribution showing the range of likely annual financial losses with confidence intervals",
                "A compliance gap analysis showing percentage of controls implemented vs. required",
            ],
            "correct_index": 2,
            "explanation": "FAIR produces probabilistic loss distributions — Monte Carlo simulations that show the range of likely outcomes (e.g., 80% confidence: losses between $1M–$8M, with a mean of $3.5M/year). This is the executive-appropriate output: it quantifies risk in financial terms that boards understand, with uncertainty explicitly represented. Heat maps (A) are subjective and ordinal. CVE reports (B) are technical. Compliance gaps (C) show control implementation, not business risk.",
            "distractor_logic": "Heat maps conflate different types of risk using subjective colour ratings — two 'red' risks may have vastly different financial impacts. CVE reports are technical artifacts for security engineers, not Board-level communication. Compliance gap analysis shows control coverage but not whether those controls actually reduce financial risk meaningfully.",
            "domain": "ciasp_d1",
            "difficulty": "medium",
        },
        {
            "text": "Which FAIR model input is MOST directly influenced by an organisation's investment in employee security awareness training?",
            "options": [
                "Threat Event Frequency (TEF) — training reduces how often threats occur",
                "Asset Value — trained employees produce more valuable work",
                "Vulnerability — training reduces the probability that a threat event results in a loss (e.g., phishing resistance)",
                "Secondary Loss — training reduces reputational damage after an incident",
            ],
            "correct_index": 2,
            "explanation": "Security awareness training primarily reduces Vulnerability — specifically the probability that a phishing attempt or social engineering attack successfully compromises an employee. Training doesn't reduce how often attackers send phishing emails (TEF remains the same), but it reduces how often employees click malicious links (Vulnerability decreases). This is the direct, measurable impact: phishing simulation click rates before and after training.",
            "distractor_logic": "TEF measures external threat actor behaviour — training doesn't stop attackers from trying. Asset Value is unrelated. Secondary Loss relates to reputational and regulatory consequences after an incident — training indirectly affects this but the primary FAIR variable it impacts is Vulnerability, the probability of successful compromise per threat event.",
            "domain": "ciasp_d1",
            "difficulty": "medium",
        },
        {
            "text": "An organisation uses cyber insurance with a $500K deductible and $10M coverage limit. A FAIR analysis shows a 95th percentile annual loss of $8M and a mean ALE of $2M. What is the MOST accurate statement?",
            "options": [
                "The insurance is unnecessary since the mean ALE is only $2M — well within budget",
                "The insurance adequately covers the 95th percentile scenario; the deductible creates a self-insured retention of $500K",
                "The insurance is insufficient since the 95th percentile exceeds the $10M limit",
                "The mean ALE of $2M should be reduced below the $500K deductible through additional controls before purchasing insurance",
            ],
            "correct_index": 1,
            "explanation": "The 95th percentile ($8M) is well within the $10M limit, so catastrophic scenarios are covered. The $500K deductible means the organisation self-insures the first $500K of any incident — a 'self-insured retention.' This is the correct risk transfer analysis. Insurance covers the tail risk (high-severity events) which is its primary purpose; the mean ALE is the expected cost and should be factored into the annual premium decision.",
            "distractor_logic": "Option A ignores tail risk — the mean is $2M but extreme events up to $8M+ can occur. Insurance is specifically valuable for tail scenarios, not just the average. Option C: the 95th percentile ($8M) is BELOW the $10M limit — it's adequately covered. Option D: reducing ALE below the deductible would only eliminate small incidents from the coverage analysis but doesn't address the tail risk that insurance is designed for.",
            "domain": "ciasp_d1",
            "difficulty": "hard",
        },
        {
            "text": "Which type of risk treatment is MOST appropriate for a scenario where the cost of mitigation ($5M/year) exceeds the ALE ($500K/year)?",
            "options": [
                "Mitigate — always implement controls to reduce risk to acceptable levels",
                "Avoid — discontinue the activity generating the risk",
                "Transfer — purchase cyber insurance to cover the $500K ALE",
                "Accept — acknowledge the risk and budget for the $500K expected annual loss",
            ],
            "correct_index": 3,
            "explanation": "When mitigation costs ($5M) significantly exceed the expected annual loss ($500K) and the risk level is within appetite, risk acceptance is the rational choice. The organisation acknowledges the risk, documents it formally, and budgets the $500K as an operational cost. This is economically optimal — spending $5M to avoid $500K of expected loss destroys $4.5M of value annually. Transfer (cyber insurance) is also viable if the premium is affordable, but acceptance is most appropriate when ALE is predictable and manageable.",
            "distractor_logic": "Mitigation at 10× cost is economically irrational — it destroys value. Avoidance means eliminating the business activity, which may eliminate the revenue generating the risk. Transfer is viable but adds premium cost for a loss that's predictable and manageable. Acceptance is optimal when ALE is known, manageable, and within risk appetite.",
            "domain": "ciasp_d1",
            "difficulty": "medium",
        },
        {
            "text": "In a FAIR analysis, what distinguishes 'Primary Loss' from 'Secondary Loss'?",
            "options": [
                "Primary Loss is direct financial loss from the threat event; Secondary Loss is loss from regulatory, legal, or reputational consequences that follow",
                "Primary Loss affects the organisation; Secondary Loss affects third parties",
                "Primary Loss is measured in dollars; Secondary Loss is measured in non-financial impact units",
                "Primary Loss occurs at the time of the incident; Secondary Loss occurs only if the incident becomes public",
            ],
            "correct_index": 0,
            "explanation": "FAIR distinguishes Primary Loss (direct losses resulting immediately from the threat event — data destruction, productivity loss, incident response costs) from Secondary Loss (losses resulting from stakeholders' reactions to the event — regulatory fines, litigation, customer churn, reputational damage). Both are financial but differ in causation: Primary from the event itself, Secondary from external parties' responses.",
            "distractor_logic": "Option B conflates the distinction with party affected — both primary and secondary can affect the organisation. Option C: both are measured in financial terms in FAIR. Option D: secondary losses can begin even if the incident is not public (e.g., an internal regulatory investigation).",
            "domain": "ciasp_d1",
            "difficulty": "easy",
        },
    ],
}


# ── Utility Functions ──────────────────────────────────────────────────────

def _get_all_questions(cert_id: str) -> List[Dict[str, Any]]:
    """
    Combine Phase 3 (ArtifactSovereign) + Phase 5 (Proctor) question banks.
    Returns shuffled merged list for the given cert.
    """
    try:
        from .artifact_sovereign_agent import _QUESTION_BANK as _PHASE3_BANK
        phase3 = list(_PHASE3_BANK.get(cert_id, []))
    except ImportError:
        phase3 = []

    phase5 = list(_PROCTOR_QUESTION_BANK.get(cert_id, []))
    merged = phase3 + phase5
    random.shuffle(merged)
    return merged


def _adaptive_select_questions(
    all_questions: List[Dict],
    n: int,
    seed_difficulty: str = "medium",
) -> List[Dict]:
    """
    Select n questions with difficulty stratification.
    For practice (10Q): 3 easy, 4 medium, 3 hard.
    For exam (30Q):     8 easy, 14 medium, 8 hard.
    Falls back to random if insufficient per-difficulty questions.
    """
    easy   = [q for q in all_questions if q.get("difficulty") == "easy"]
    medium = [q for q in all_questions if q.get("difficulty") == "medium"]
    hard   = [q for q in all_questions if q.get("difficulty") == "hard"]

    if n <= 10:
        targets = [("easy", 3), ("medium", 4), ("hard", 3)]
    else:
        targets = [("easy", 8), ("medium", 14), ("hard", 8)]

    selected = []
    pools = {"easy": easy, "medium": medium, "hard": hard}

    for diff, count in targets:
        pool = pools[diff]
        random.shuffle(pool)
        selected.extend(pool[:count])

    # If we still need more, fill from remaining
    if len(selected) < n:
        remainder = [q for q in all_questions if q not in selected]
        random.shuffle(remainder)
        selected.extend(remainder[:n - len(selected)])

    # Shuffle final selection to mix difficulties
    random.shuffle(selected)
    return selected[:n]


def _clean_expired_sessions() -> None:
    """Remove sessions older than SESSION_TTL. Called lazily."""
    now = time.time()
    expired = [sid for sid, s in _SESSIONS.items() if now - s["start_time"] > SESSION_TTL]
    for sid in expired:
        logger.debug("Expiring session %s", sid)
        del _SESSIONS[sid]


def _compute_readiness_score(
    cert_id: str,
    answers: List[Optional[int]],
    questions: List[Dict],
    difficulty_log: List[str],
) -> Dict[str, Any]:
    """
    Compute IRT-based readiness score.
    θ (ability) = weighted correct / weighted total, mapped to [-3, +3].
    P(pass) = sigmoid(k × (θ - b)).
    """
    weights = {"easy": 1, "medium": 2, "hard": 3}

    weighted_correct = 0
    weighted_total   = 0
    domain_stats: Dict[str, Dict[str, int]] = {}

    for i, (q, ans) in enumerate(zip(questions, answers)):
        if ans is None:
            continue
        diff   = q.get("difficulty", "medium")
        w      = weights[diff]
        domain = q.get("domain", "unknown")
        correct = (ans == q["correct_index"])

        weighted_total   += w
        weighted_correct += w if correct else 0

        if domain not in domain_stats:
            domain_stats[domain] = {"attempts": 0, "correct": 0, "score": 0}
        domain_stats[domain]["attempts"] += 1
        if correct:
            domain_stats[domain]["correct"] += 1

    if weighted_total == 0:
        return {
            "readiness_score": 0,
            "pass_probability_pct": 0,
            "domain_stats": {},
            "weakness_domains": [],
        }

    # Map to [-3, +3] ability scale
    ratio = weighted_correct / weighted_total  # 0..1
    theta = (ratio * 6) - 3  # maps 0→-3, 0.5→0, 1→+3

    # IRT sigmoid
    b = _CERT_DIFFICULTY_THRESHOLD.get(cert_id, 0.55)
    b_scaled = (b * 6) - 3  # convert threshold to same scale
    exponent = -_IRT_K * (theta - b_scaled)
    p_pass = 1 / (1 + math.exp(exponent))
    p_pass = min(0.99, max(0.01, p_pass))  # clamp

    # Domain scores
    for d in domain_stats:
        s = domain_stats[d]
        s["score"] = round(100 * s["correct"] / max(1, s["attempts"]))

    weakness_domains = sorted(
        [d for d, s in domain_stats.items() if s["score"] < 60],
        key=lambda d: domain_stats[d]["score"],
    )

    return {
        "readiness_score":     round(p_pass * 100),
        "pass_probability_pct": round(p_pass * 100),
        "weighted_correct":    weighted_correct,
        "weighted_total":      weighted_total,
        "domain_stats":        domain_stats,
        "weakness_domains":    weakness_domains,
    }


# ── Public Session API ─────────────────────────────────────────────────────

def create_session(
    cert_id: str,
    mode: str,
    user_id: str = "anonymous",
) -> Dict[str, Any]:
    """
    Create a new exam session.
    Returns: {session_id, cert_id, mode, time_limit_secs, total_questions, status}
    """
    _clean_expired_sessions()

    cert_id = cert_id.lower()
    mode    = mode.lower()
    if mode not in ("practice", "exam"):
        mode = "practice"

    n_questions = PRACTICE_Q_COUNT if mode == "practice" else EXAM_Q_COUNT
    time_limit  = None if mode == "practice" else EXAM_TIME_LIMIT

    all_qs  = _get_all_questions(cert_id)
    selected = _adaptive_select_questions(all_qs, n_questions)

    if len(selected) < n_questions:
        # Repeat questions with shuffled option order if bank is small
        extra_needed = n_questions - len(selected)
        pool = list(all_qs) * 3  # triple the bank
        random.shuffle(pool)
        for q in pool:
            if len(selected) >= n_questions:
                break
            if q not in selected:
                selected.append(q)

    session_id = str(uuid.uuid4())
    session = {
        "session_id":           session_id,
        "user_id":              user_id,
        "cert_id":              cert_id,
        "mode":                 mode,
        "questions":            selected,
        "current_idx":          0,
        "answers":              [None] * len(selected),
        "difficulty":           "medium",
        "consecutive_correct":  0,
        "consecutive_wrong":    0,
        "difficulty_log":       [],
        "start_time":           time.time(),
        "time_limit_secs":      time_limit,
        "status":               "active",
        "total_questions":      len(selected),
    }
    _SESSIONS[session_id] = session

    return {
        "session_id":     session_id,
        "cert_id":        cert_id,
        "mode":           mode,
        "total_questions": len(selected),
        "time_limit_secs": time_limit,
        "status":         "active",
    }


def get_current_question(session_id: str) -> Dict[str, Any]:
    """
    Return the current question (without correct_index or explanation).
    """
    session = _SESSIONS.get(session_id)
    if not session:
        return {"error": "Session not found or expired"}
    if session["status"] != "active":
        return {"error": "Session is not active", "status": session["status"]}

    idx = session["current_idx"]
    if idx >= len(session["questions"]):
        return {"error": "No more questions — session complete", "status": "completed"}

    q = session["questions"][idx]
    elapsed = time.time() - session["start_time"]

    return {
        "question_number": idx + 1,
        "total_questions": session["total_questions"],
        "question_id":     idx,
        "text":            q["text"],
        "options":         q["options"],
        "domain":          q.get("domain", ""),
        "difficulty":      q.get("difficulty", "medium"),
        "current_difficulty": session["difficulty"],
        "elapsed_secs":    round(elapsed),
        "time_limit_secs": session.get("time_limit_secs"),
        "status":          "active",
    }


def submit_answer(session_id: str, answer_index: int) -> Dict[str, Any]:
    """
    Record user's answer, apply adaptive difficulty, return feedback.
    In exam mode: explanation is deferred (not returned until results).
    """
    session = _SESSIONS.get(session_id)
    if not session:
        return {"error": "Session not found or expired"}
    if session["status"] != "active":
        return {"error": "Session not active", "status": session["status"]}

    idx = session["current_idx"]
    if idx >= len(session["questions"]):
        return {"error": "Session complete — no more questions to answer"}

    q       = session["questions"][idx]
    correct = (answer_index == q["correct_index"])

    # Record answer
    session["answers"][idx] = answer_index

    # Adaptive difficulty
    if correct:
        session["consecutive_correct"] += 1
        session["consecutive_wrong"]   = 0
        if session["consecutive_correct"] >= _DIFFICULTY_UPGRADE_THRESHOLD and session["difficulty"] != "hard":
            session["difficulty"] = "hard"
            session["consecutive_correct"] = 0
    else:
        session["consecutive_wrong"]   += 1
        session["consecutive_correct"] = 0
        if session["consecutive_wrong"] >= _DIFFICULTY_DOWNGRADE_THRESHOLD and session["difficulty"] != "easy":
            session["difficulty"] = "easy"
            session["consecutive_wrong"] = 0

    session["difficulty_log"].append(session["difficulty"])

    # Advance to next question
    session["current_idx"] += 1
    is_last = session["current_idx"] >= session["total_questions"]

    if is_last:
        session["status"] = "completed"

    response: Dict[str, Any] = {
        "correct":          correct,
        "is_last":          is_last,
        "question_number":  idx + 1,
        "total_questions":  session["total_questions"],
        "current_difficulty": session["difficulty"],
    }

    # Practice mode: immediate feedback
    if session["mode"] == "practice":
        response["correct_index"]   = q["correct_index"]
        response["explanation"]     = q.get("explanation", "")
        response["distractor_logic"] = q.get("distractor_logic", "")

    return response


def get_results(session_id: str) -> Dict[str, Any]:
    """
    Return full results including readiness score, domain analysis, and answer review.
    Updates the user's weakness store.
    """
    session = _SESSIONS.get(session_id)
    if not session:
        return {"error": "Session not found or expired"}

    # Force-complete if called before session finishes
    if session["status"] == "active":
        session["status"] = "completed"

    cert_id   = session["cert_id"]
    questions = session["questions"]
    answers   = session["answers"]
    mode      = session["mode"]

    # Compute readiness
    readiness = _compute_readiness_score(
        cert_id, answers, questions, session.get("difficulty_log", [])
    )

    # Build answer review (always returned in results)
    review = []
    correct_count = 0
    for i, (q, ans) in enumerate(zip(questions, answers)):
        was_correct = (ans == q["correct_index"]) if ans is not None else False
        if was_correct:
            correct_count += 1
        review.append({
            "question_number": i + 1,
            "text":            q["text"],
            "options":         q["options"],
            "user_answer_idx": ans,
            "correct_index":   q["correct_index"],
            "correct":         was_correct,
            "explanation":     q.get("explanation", ""),
            "distractor_logic": q.get("distractor_logic", ""),
            "domain":          q.get("domain", ""),
            "difficulty":      q.get("difficulty", "medium"),
        })

    # Update weakness store
    user_id = session.get("user_id", "anonymous")
    if user_id not in _WEAKNESS_STORE:
        _WEAKNESS_STORE[user_id] = {}
    for d, stats in readiness["domain_stats"].items():
        if d not in _WEAKNESS_STORE[user_id]:
            _WEAKNESS_STORE[user_id][d] = {"attempts": 0, "correct": 0}
        _WEAKNESS_STORE[user_id][d]["attempts"] += stats["attempts"]
        _WEAKNESS_STORE[user_id][d]["correct"]  += stats["correct"]

    passing_score = _CERT_PASSING_SCORE.get(cert_id, 70)
    raw_pct = round(100 * correct_count / max(1, len(questions)))

    return {
        "session_id":          session_id,
        "cert_id":             cert_id,
        "mode":                mode,
        "total_questions":     session["total_questions"],
        "correct_count":       correct_count,
        "raw_score_pct":       raw_pct,
        "readiness_score":     readiness["readiness_score"],
        "pass_probability_pct": readiness["pass_probability_pct"],
        "domain_stats":        readiness["domain_stats"],
        "weakness_domains":    readiness["weakness_domains"],
        "answer_review":       review,
        "elapsed_secs":        round(time.time() - session["start_time"]),
    }


def get_weakness_report(user_id: str) -> Dict[str, Any]:
    """Return aggregated weakness data across all sessions for this user."""
    store = _WEAKNESS_STORE.get(user_id, {})
    if not store:
        return {"domains": {}, "weakest_domains": [], "sessions_analysed": 0}

    domain_scores = {}
    for d, s in store.items():
        pct = round(100 * s["correct"] / max(1, s["attempts"]))
        domain_scores[d] = {
            "attempts": s["attempts"],
            "correct":  s["correct"],
            "score_pct": pct,
            "status": "weak" if pct < 60 else "improving" if pct < 80 else "strong",
        }

    weakest = sorted(
        [d for d, s in domain_scores.items() if s["score_pct"] < 80],
        key=lambda d: domain_scores[d]["score_pct"],
    )

    return {
        "domains":         domain_scores,
        "weakest_domains": weakest,
        "sessions_analysed": len(set(
            # Rough proxy: count unique cert exposures
            d.split("_")[0] for d in store.keys()
        )),
    }


# ── Agent Class ────────────────────────────────────────────────────────────

class ProctorAgent(BaseAgent):
    """
    Phase 5 — Proctor Agent.

    The agent's run() method is called for session creation only.
    Subsequent question/answer/result interactions use the module-level
    functions directly (stateful, not agent-per-request pattern).

    Input:  {
        "action":  "create_session" | "get_weakness",
        "cert_id": "aigp" | "cisa" | "aaia" | "ciasp",
        "mode":    "practice" | "exam",
        "user_id": str,
    }
    Output: session dict or weakness report
    """

    name          = "proctor_agent"
    resource_tier = ResourceTier.HEAVY

    async def _execute(self, input_data: Dict[str, Any]) -> AgentResult:
        action  = input_data.get("action", "create_session")
        user_id = input_data.get("user_id", "anonymous")

        try:
            if action == "create_session":
                cert_id = input_data.get("cert_id", "aigp")
                mode    = input_data.get("mode", "practice")
                result  = create_session(cert_id, mode, user_id)
                return AgentResult(success=True, data=result)

            elif action == "get_weakness":
                result = get_weakness_report(user_id)
                return AgentResult(success=True, data=result)

            else:
                return AgentResult(
                    success=False,
                    error=f"Unknown action: {action}. Use 'create_session' or 'get_weakness'.",
                )

        except Exception as exc:
            logger.exception("ProctorAgent error: %s", exc)
            return AgentResult(success=False, error=str(exc))
