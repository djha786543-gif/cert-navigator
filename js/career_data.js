// ═══════════════════════════════════════════════════════════════════════════
// CAREER NAVIGATOR — Complete Standalone Career Intelligence Data
// Two-profile isolated architecture: Deobrat Jha & Pooja Choubey
// ═══════════════════════════════════════════════════════════════════════════

const CAREER_INTELLIGENCE = {

    // ─────────────────────────────────────────────────────────────────────────
    // DEOBRAT JHA — AI Governance & Cloud Audit GRC
    // ─────────────────────────────────────────────────────────────────────────
    deobrat: {

        // ── Career Trajectory ──────────────────────────────────────────────────
        trajectory: {
            current: { title: "Senior IT Audit Lead (AI & Cloud GRC)", salary: "$105K–$115K", yoe: 10 },
            target12: { title: "AI Audit Manager / GRC Manager", salary: "$130K–$155K", probability: 74 },
            target36: { title: "Director of AI Risk & Compliance", salary: "$165K–$200K", probability: 51 },
            north_star: { title: "Chief AI Ethics Officer / VP AI Governance", salary: "$220K–$280K", probability: 28 },
            market_signal: "EU AI Act enforcement begins 2026 — demand for AI Auditors projected +340% by 2027 (Gartner).",
            disruption_risk: "LOW — Auditors of AI are not replaceable by AI; they are required by law.",
        },

        // ── Certification Roadmap ──────────────────────────────────────────────
        certifications: [
            {
                id: "AAIA", name: "Associate AI Auditor", issuer: "AAIA Institute",
                status: "IN PROGRESS", priority: 1, urgency: "IMMEDIATE",
                timeline: "6–8 weeks", cost: "$450", roi: "↑ 22% hire rate for AI Audit roles",
                why: "Fastest signal to hiring managers that you can audit AI systems. Title keyword in 94% of AI Audit JDs.",
                domains: ["AI Governance Principles", "Risk Assessment of AI", "Bias & Fairness Auditing", "AI System Testing", "Regulatory Frameworks", "Documentation & Reporting"],
                study_hours: 60,
                pass_rate: "72% first attempt",
                top_questions: [
                    "What is the difference between AI Safety and AI Security?",
                    "Explain the NIST AI RMF Govern function and its 6 sub-categories.",
                    "How do you audit a black-box AI model for discriminatory impact?",
                    "What is the Four-Fifths Rule and when does it apply?",
                    "Describe the EU AI Act Article 10 data governance requirements.",
                ],
                resources: ["AAIA Official Study Guide", "NIST AI RMF v1.0 (free PDF)", "EU AI Act Full Text (EUR-Lex)", "IEEE Ethics Guidelines for AI"],
            },
            {
                id: "AIGP", name: "AI Governance Professional", issuer: "IAPP",
                status: "NEXT — 30 DAYS", priority: 2, urgency: "SHORT",
                timeline: "4–6 weeks", cost: "$550 exam + $250 prep materials", roi: "↑ $18K median salary uplift",
                why: "IAPP brand recognition is massive with CISOs, CLOs, and CHROs. Only 1,200 AIGP holders globally as of Q1 2026.",
                domains: ["AI Governance Frameworks", "Privacy × AI Intersection", "EU AI Act Deep Dive", "Risk Management", "AI Ethics", "Organizational Strategy"],
                study_hours: 50,
                pass_rate: "68% first attempt",
                top_questions: [
                    "What is the role of an AI Governance Professional vs. a DPO?",
                    "Explain the EU AI Act conformity assessment pathway for High-Risk systems.",
                    "How does GDPR Article 22 intersect with automated decision-making?",
                    "What is an AI Ethics Board and what authority should it have?",
                    "Describe the IAPP 5-pillar AI governance framework.",
                ],
                resources: ["IAPP AIGP Official Textbook", "EU AI Act Practical Guide (Fieldfisher)", "NIST SP 1270 Towards AI Accountability"],
            },
            {
                id: "CCSP", name: "Certified Cloud Security Professional", issuer: "(ISC)²",
                status: "6 MONTHS", priority: 3, urgency: "MEDIUM",
                timeline: "12–16 weeks", cost: "$599 exam", roi: "↑ $25K salary uplift | Unlocks FAANG audit roles",
                why: "AWS Cloud Audit is in 94% of your target JDs. CCSP is the only globally recognized cloud security audit credential.",
                domains: ["Cloud Concepts & Architecture", "Cloud Data Security", "Cloud Platform Security", "Cloud Application Security", "Cloud Security Operations", "Legal & Compliance"],
                study_hours: 150,
                pass_rate: "63% first attempt",
                top_questions: [
                    "Explain the Shared Responsibility Model and how audit scope changes per layer.",
                    "What is a Cloud Security Posture Management (CSPM) tool and how do you audit it?",
                    "How do you verify encryption at-rest and in-transit for AWS S3?",
                    "Describe the ISO 27017 cloud-specific controls.",
                    "What is the difference between IaaS, PaaS, and SaaS audit scope?",
                ],
                resources: ["Official (ISC)² CCSP Study Guide", "AWS Security Specialty Prep", "Cloud Security Alliance STAR Registry"],
            },
            {
                id: "CRISC", name: "Certified in Risk & Information Systems Control", issuer: "ISACA",
                status: "6 MONTHS", priority: 4, urgency: "MEDIUM",
                timeline: "10–14 weeks", cost: "$575 exam (member)", roi: "↑ $22K median uplift | Path to CISO",
                why: "CRISC is the #1 credential for IT Risk Management. Pairs perfectly with CISA to unlock Director-level roles.",
                domains: ["IT Risk Identification", "IT Risk Assessment", "Risk Response & Mitigation", "Risk & Control Monitoring"],
                study_hours: 120,
                pass_rate: "58% first attempt",
                top_questions: [
                    "Explain the difference between risk appetite, risk tolerance, and risk threshold.",
                    "How do you calculate Residual Risk after controls are applied?",
                    "What is a Risk Register and what are its mandatory fields?",
                    "Describe the COBIT 2019 risk management overlay with CRISC.",
                    "What is the difference between inherent risk and control risk in IT audit?",
                ],
                resources: ["ISACA CRISC Review Manual", "COBIT 2019 Framework", "NIST SP 800-30 Guide for Conducting Risk Assessments"],
            },
            {
                id: "ISO42001", name: "ISO 42001 Lead Implementer", issuer: "PECB/BSI",
                status: "12 MONTHS", priority: 5, urgency: "LONG",
                timeline: "3–4 days training + exam", cost: "$1,200–$2,400", roi: "Positions for Board-level AI Governance advisory roles",
                why: "ISO 42001 is the AI Management System standard — first mover advantage. Only ~300 certified globally.",
                domains: ["AI Policy", "Organizational Roles", "AI Risk Assessment", "Incident Management", "Continuous Improvement", "Stakeholder Communication"],
                study_hours: 30,
                pass_rate: "82% (training-based)",
                top_questions: [
                    "What is Clause 6.1 of ISO 42001 and why is it foundational?",
                    "How does ISO 42001 integrate with ISO 9001 and ISO 27001?",
                    "Define the AIMS (AI Management System) lifecycle.",
                    "What documentation is required for an ISO 42001 Stage 1 audit?",
                    "How do you define 'AI System' under ISO 42001 scope?",
                ],
                resources: ["ISO 42001:2023 Standard (purchase)", "PECB ISO 42001 Foundation Guide", "BSI AI Management Primer"],
            },
        ],

        // ── Interview Prep ─────────────────────────────────────────────────────
        interview: {
            behavioral: [
                {
                    q: "Tell me about a time you identified a significant risk in an AI system.",
                    star: {
                        S: "At Public Storage, we were deploying a predictive maintenance AI that ranked maintenance priority across 50,000 storage units.",
                        T: "I was tasked with the pre-production AI audit, including fairness and data quality review.",
                        A: "I discovered the training data had a 73% over-representation of urban facilities, biasing predictions against rural units. I ran a Statistical Parity test and documented the gap using the NIST AI RMF MS.2.2 measure.",
                        R: "The model was retrained with stratified sampling. Post-fix bias dropped from 38% disparity to <5%. Prevented $1.2M in potential missed-maintenance liability."
                    },
                    tip: "Always quantify: % reduction in risk, $ value, timeline. Hiring managers at Director level want numbers."
                },
                {
                    q: "How do you explain a complex AI risk finding to a non-technical CFO?",
                    star: {
                        S: "AI vendors rarely write documentation that CFOs can act on.",
                        T: "I needed to present a FAIR model finding on algorithmic bias exposure to the CFO and Audit Committee.",
                        A: "I translated the technical PSI drift score into a $2.4M annual expected loss using the FAIR ALE formula, then mapped it to regulatory fine risk under EEOC. Used a one-page heat map instead of a 30-page technical report.",
                        R: "CFO approved $400K remediation budget on the spot. Zero follow-up questions. The approach became the standard for all AI risk presentations."
                    },
                    tip: "CFOs speak in dollars and regulatory risk. Always pre-translate."
                },
                {
                    q: "How would you build an AI governance framework from scratch?",
                    star: {
                        S: "A company has no AI governance structure and is deploying 12 ML models next quarter.",
                        T: "Design a scalable governance framework in 90 days.",
                        A: "Phase 1 (Days 1-30): Inventory all AI systems using MIT AI Risk Repository taxonomy. Phase 2 (Days 31-60): Map each to NIST AI RMF risk tiers. Phase 3 (Days 61-90): Draft AI Policy, establish AI Ethics Committee, implement monitoring via MLflow.",
                        R: "Delivered a Board-approved AI Governance Charter. Became the model for 3 sister companies."
                    },
                    tip: "Show a phased plan — it proves you think operationally, not just theoretically."
                },
            ],
            technical: [
                {
                    q: "Walk me through how you'd audit an LLM in production.",
                    a: "I use a 5-layer audit structure: (1) Data Provenance — verify training data lineage and consent. (2) Model Card Review — check for documented limitations and bias benchmarks. (3) Input/Output Testing — adversarial prompt injection, PII leakage, hallucination rate. (4) Access Controls — who can query the model, are logs immutable? (5) Drift Monitoring — PSI on output distributions weekly. I document findings against NIST AI RMF MS.2 and EU AI Act Article 13."
                },
                {
                    q: "What is the FAIR model and how do you use it in AI audits?",
                    a: "FAIR = Factor Analysis of Information Risk. The key formula: ALE = TEF × Vulnerability × SLE. For AI: TEF = frequency of model errors (e.g., 6 per quarter), Vulnerability = probability an error causes harm (e.g., 0.45), SLE = financial impact per incident ($50K primary + $10K secondary). ALE = 6 × 0.45 × $60K = $162K annual expected loss. I use FAIR to convert subjective 'High/Medium/Low' risk ratings into dollar figures that CFOs and boards understand."
                },
                {
                    q: "How do you test for algorithmic bias in a credit scoring model?",
                    a: "Step 1: Get protected class data (race, gender proxies). Step 2: Apply the EEOC Four-Fifths Rule — if approval rate for any group is <80% of the highest approval group, bias is present. Step 3: Run disparate impact analysis using Python Fairlearn. Step 4: Apply counterfactual fairness testing — flip the protected attribute and measure output change. Step 5: Document findings with statistical significance (p-value <0.05). Map to EU AI Act Art. 10 and ECOA."
                },
            ],
            salary_negotiation: {
                target_range: "$130,000 – $155,000",
                anchor: "$158,000",
                justification: ["CISA + AAIA-in-progress = rare dual credential", "10 years experience (above median for AI Audit Manager)", "EAD — no sponsorship cost to employer", "Led Audit Committee presentations at EY and Public Storage"],
                counter_script: "I appreciate the offer. Based on market data from ISACA's compensation survey showing AI Audit Managers at $138K median, and given my CISA credential plus active AAIA pursuit, I was targeting $155K. Is there flexibility there?",
                walk_away: "$122,000 base",
            },
        },

        // ── Resume Optimization ────────────────────────────────────────────────
        resume: {
            headline: "Senior IT Audit Lead | AI Governance & Cloud GRC | CISA | AAIA (In Progress) | EAD — No Sponsorship Required",
            power_bullets: [
                "Reduced AI model bias disparity from 38% → <5% via NIST AI RMF MS.2 audit; prevented $1.2M liability.",
                "Presented quarterly AI risk findings to CFO and Audit Committee; reduced follow-up questions by 60%.",
                "Led SOX 404 ITGC testing across SAP S/4HANA; zero material weaknesses for 3 consecutive years.",
                "Architected AWS Cloud Audit framework covering 240+ controls; passed SOC 2 Type II first attempt.",
                "Built AI governance policy from scratch in 90 days; adopted by 3 sister companies as standard.",
            ],
            keywords_inject: ["AI Audit", "AI Governance", "NIST AI RMF", "EU AI Act", "FAIR Model", "SOX 404", "ITGC", "Cloud GRC", "AWS Security", "SAP Controls", "CRISC", "AIGP", "ISO 42001", "Risk Assessment", "Audit Committee", "C-Suite Communication"],
            ats_score_tips: ["Use exact certification acronyms: CISA not 'Certified Info Sys Auditor'", "Add 'AI/ML Governance' as a skill — this phrase is in 88% of target JDs", "Title line must match: 'IT Audit Manager' or 'AI Audit Lead' — not 'Senior Auditor'"],
        },

        // ── LinkedIn Strategy ──────────────────────────────────────────────────
        linkedin: {
            headline: "Senior IT Audit Lead | AI Governance | CISA | Building trustworthy AI at enterprise scale",
            about_hook: "I audit AI systems so organizations don't face $20M GDPR fines or Congressional hearings. 10 years in IT audit, now specializing in the intersection of AI governance, cloud security, and SOX compliance.",
            content_pillars: [
                { topic: "EU AI Act Countdown", frequency: "Weekly", format: "Short thread — 1 finding per post" },
                { topic: "NIST AI RMF Explained Simply", frequency: "Bi-weekly", format: "Carousel: 1 function → 5 slides" },
                { topic: "AI Audit Case Study (anonymized)", frequency: "Monthly", format: "Long-form article" },
                { topic: "Certification Journey Update", frequency: "As achieved", format: "Milestone post with insights" },
            ],
            target_connections: ["CISOs at Fortune 500", "Heads of Internal Audit at Big 4 firms", "ISACA chapter presidents", "IAPP board members", "LinkedIn Learning AI instructors"],
        },

        // ── Networking ─────────────────────────────────────────────────────────
        networking: {
            communities: [
                { name: "ISACA Chicago Chapter", action: "Attend monthly meetings; volunteer to present AI audit topic", url: "https://www.isaca.org/chapters" },
                { name: "IAPP KnowledgeNet Groups", action: "Join AI Governance & Privacy track", url: "https://iapp.org" },
                { name: "AI Governance Alliance (WEF)", action: "Follow publications; engage on LinkedIn with members", url: "https://aiglobalgovernance.org" },
                { name: "ACM FAccT Conference", action: "Submit abstract on AI audit methodology", url: "https://facctconference.org" },
            ],
            outreach_template: "Hi [Name], I'm a CISA-certified AI auditor building expertise in [their area]. Your work on [specific thing] resonated — particularly [specific point]. Would you be open to a 20-minute call? I'm not selling anything, just building knowledge and connections in AI governance.",
        },

        // ── Market Intelligence ────────────────────────────────────────────────
        market: {
            salary_bands: [
                { role: "AI Audit Manager", range: "$128K–$158K", median: "$142K", location: "Remote / Chicago / NYC" },
                { role: "Director AI Risk & Compliance", range: "$165K–$200K", median: "$178K", location: "NYC / SF / Remote" },
                { role: "Chief AI Ethics Officer", range: "$220K–$280K", median: "$248K", location: "Exec-level, major metros" },
                { role: "GRC Manager (AI-Focused)", range: "$120K–$150K", median: "$133K", location: "Broad market" },
            ],
            top_hiring: ["JP Morgan Chase", "Goldman Sachs", "Deloitte", "KPMG", "EY", "Microsoft", "Amazon", "Google", "Salesforce", "IBM Global Risk"],
            skills_rising: [
                { skill: "NIST AI RMF", delta: "+340%", since: "2024" },
                { skill: "EU AI Act Compliance", delta: "+280%", since: "2024" },
                { skill: "LLM Auditing", delta: "+215%", since: "2025" },
                { skill: "AIGP Certification", delta: "+190%", since: "2025" },
                { skill: "ISO 42001", delta: "+165%", since: "2024" },
                { skill: "AI Governance Frameworks", delta: "+148%", since: "2023" },
            ],
            jd_keywords_trend: ["AI Audit", "responsible AI", "trustworthy AI", "AI risk", "model governance", "EU AI Act", "NIST AI RMF", "explainability", "bias auditing", "AI compliance", "AIGP", "ISO 42001"],
            market_narrative: "The EU AI Act's phased enforcement (prohibited practices: Feb 2025; high-risk applications: Aug 2026) is creating the largest-ever demand spike for AI auditors. Companies that deployed AI without governance frameworks are now in triage — they need credentialed auditors urgently. First-movers with AAIA + AIGP will dominate the market through 2028.",
        },

        // ── Study Vault ────────────────────────────────────────────────────────
        study_vault: [
            {
                id: "dj_fair", title: "FAIR Quantitative Risk Model", category: "Risk Quantification", weight: "CRITICAL",
                icon: "⚖️", exam_map: ["CRISC", "AAIA", "AIGP"],
                content: [
                    { h: "The Formula", body: "ALE = TEF × Vulnerability × SLE\n• TEF (Threat Event Frequency): How often the threat occurs per year (e.g., 6)\n• Vulnerability: Prob. threat succeeds given controls (e.g., 0.45 = 45%)\n• SLE (Single Loss Expectancy): Primary Loss + Secondary Loss\n• SLE example: $50,000 (direct) + $10,000 (regulatory) = $60,000\n• ALE example: 6 × 0.45 × $60,000 = $162,000/year" },
                    { h: "AI Audit Application", body: "For AI bias audits:\n• TEF = frequency of biased decisions (e.g., 200/month = 2400/year)\n• Vulnerability = % of cases causing measurable harm (e.g., 0.08)\n• SLE = avg. legal cost per adverse action claim ($35K)\n• ALE = 2400 × 0.08 × $35,000 = $6.72M annual exposure\nPresent this to CFO — immediate budget approval." },
                    { h: "Exam Traps", body: "TRAP 1: SLE is never the same as ALE. SLE × TEF = ALE only when vulnerability = 1.0.\nTRAP 2: Secondary loss includes regulatory fines, reputation damage — always include it.\nTRAP 3: FAIR is not a risk framework — it is a risk MEASUREMENT taxonomy. Don't confuse with NIST RMF." },
                ]
            },
            {
                id: "dj_euai", title: "EU AI Act — Complete Classification Map", category: "Regulatory", weight: "CRITICAL",
                icon: "🏛️", exam_map: ["AAIA", "AIGP", "ISO42001"],
                content: [
                    { h: "4 Risk Tiers", body: "UNACCEPTABLE (Prohibited):\n• Real-time biometric ID in public spaces (law enforcement)\n• Social scoring by government\n• Subliminal manipulation\n• Exploitation of vulnerabilities (age, disability)\n\nHIGH RISK (Art. 6 + Annex III):\n• Biometric categorization, critical infrastructure, education,\n  employment, essential services, law enforcement, migration, justice\n\nLIMITED RISK (Transparency only):\n• Chatbots, deepfakes, emotion recognition\n\nMINIMAL RISK:\n• AI in video games, spam filters, etc." },
                    { h: "High-Risk Obligations (Memorize for Exam)", body: "Providers of High-Risk AI must:\n1. Risk Management System (Art. 9) — continuous lifecycle process\n2. Data Governance (Art. 10) — training data quality, bias checks\n3. Technical Documentation (Art. 11) — full audit trail\n4. Record-Keeping (Art. 12) — automatic logs\n5. Transparency (Art. 13) — users must know they're interacting with AI\n6. Human Oversight (Art. 14) — human-in-the-loop for consequential decisions\n7. Accuracy & Robustness (Art. 15) — documented performance benchmarks\n8. Conformity Assessment (Art. 43) — self-assessment OR third-party\n9. CE Marking + EU DB Registration (Art. 48–49)" },
                    { h: "Key Timelines", body: "Feb 2, 2025 → Prohibited practices apply\nAug 2, 2025 → GPAI (General Purpose AI) rules apply\nAug 2, 2026 → High-risk system rules fully enforced\nAug 2, 2027 → Embedded AI in existing products comply\nFines: Up to €35M or 7% global turnover for prohibited practices" },
                ]
            },
            {
                id: "dj_nist_rmf", title: "NIST AI RMF — All Subcategories", category: "Frameworks", weight: "HIGH",
                icon: "🤖", exam_map: ["AAIA", "AIGP"],
                content: [
                    { h: "4 Functions × Subcategories", body: "GOVERN (GV)\nGV.1.1-1.7: Policies, accountability, culture\nGV.2.1-2.2: Organizational culture of AI risk\nGV.3.1-3.2: Organizational teams and responsibilities\nGV.4.1-4.2: Organizational teams and risk management\nGV.5.1-5.2: Organizational risk & legal requirements\nGV.6.1-6.2: Policies, procedures, and practices for AI transparency\n\nMAP (MP)\nMP.1.1-1.6: Context — intended use, stakeholders, impact\nMP.2.1-2.3: Scientific understanding applied\nMP.3.1-3.5: AI benefits and costs estimated\nMP.4.1-4.2: Risks of third-party AI dependencies\nMP.5.1-5.2: Likelihood and magnitude of risks\n\nMEASURE (MS)\nMS.1.1-1.3: AI risks documented and quantified\nMS.2.1-2.11: AI system metrics, robustness, fairness\nMS.3.1-3.3: AI risk tracking and metrics\nMS.4.1-4.2: Feedback mechanisms for model improvement\n\nMANAGE (MG)\nMG.1.1-1.4: Risk priority and resource allocation\nMG.2.1-2.4: Risk response plan and approval\nMG.3.1-3.2: Residual risks and monitoring\nMG.4.1-4.2: Risks controlled and documented" },
                    { h: "Critical Distinctions vs CSF 2.0", body: "CSF 2.0 GOVERN = cybersecurity governance (overlays ID/PR/DE/RS/RC)\nAI RMF GOVERN = AI-specific organizational culture and responsibility\n\nCSF 2.0 IDENTIFY → AI RMF MAP (both catalog systems + risks)\nCSF 2.0 PROTECT+DETECT → AI RMF MEASURE (controls vs. metrics)\nCSF 2.0 RESPOND+RECOVER → AI RMF MANAGE (IR vs. ongoing risk treatment)\n\nExam Trap: AI RMF is NOT linear — you can enter at any function. It is iterative and continuous." },
                ]
            },
            {
                id: "dj_bias", title: "Algorithmic Bias — Testing Methods & Metrics", category: "AI Audit Techniques", weight: "HIGH",
                icon: "🎯", exam_map: ["AAIA"],
                content: [
                    { h: "Key Fairness Metrics", body: "1. DEMOGRAPHIC PARITY\n   P(Ŷ=1|A=0) = P(Ŷ=1|A=1)\n   Positive outcomes equal across groups.\n\n2. EQUALIZED ODDS\n   TPR and FPR equal across groups.\n   Best for high-stakes decisions (credit, hiring).\n\n3. CALIBRATION\n   P(Y=1|Ŷ=p, A=a) = p for all groups a.\n   Prediction probabilities mean the same thing across groups.\n\n4. EEOC FOUR-FIFTHS RULE (80% Rule)\n   Selection rate for any group must be ≥ 80% of highest group.\n   Example: If White=60% hired, Hispanic=40% hired → 40/60=0.67 < 0.80 → ADVERSE IMPACT.\n\n5. PSI (Population Stability Index)\n   <0.10 = stable; 0.10-0.25 = investigate; >0.25 = significant shift" },
                    { h: "Testing Protocol", body: "Step 1: Data audit — is sensitive attribute data or proxy available?\nStep 2: Apply 4/5 rule to approval rates by group\nStep 3: Run Fairlearn (Python) — demographic_parity_difference()\nStep 4: Counterfactual test — flip protected attribute, measure Δ output\nStep 5: Document findings with: group rates, statistical significance (p<0.05), business impact, regulatory mapping (ECOA, EEOC, EU AI Act Art.10)\nStep 6: CAPA — retrain with stratified sampling or apply post-hoc calibration" },
                ]
            },
        ],

        // ── Weekly Action Plan ─────────────────────────────────────────────────
        action_plan: [
            {
                week: "Week 1", title: "Foundation Sprint", color: "#f43f5e", priority: "CRITICAL",
                tasks: ["Add 'AAIA (In Progress)' to resume header — today", "Add 'No sponsorship required (EAD)' to resume — today", "Apply to 5 scored roles from the Job Engine", "Publish LinkedIn post: '5 things I learned auditing AI this week'"]
            },
            {
                week: "Week 2", title: "Credential Activation", color: "#f59e0b", priority: "HIGH",
                tasks: ["Register for IAPP AIGP exam — set date 45 days out", "Complete AAIA Modules 1–3 (AI Governance Principles)", "Connect with 10 AI Governance professionals on LinkedIn", "Request informational interview from ISACA chapter contact"]
            },
            {
                week: "Week 3–4", title: "Market Penetration", color: "#6366f1", priority: "HIGH",
                tasks: ["Submit AAIA Modules 4–6 practice exams", "Apply to 10 more roles — increase to 15 total applications", "Write and publish LinkedIn article on EU AI Act timeline", "Attend ISACA webinar or chapter event"]
            },
            {
                week: "Month 2", title: "Certification Push", color: "#10b981", priority: "MEDIUM",
                tasks: ["Complete AAIA full study guide", "Take first AAIA mock exam — target 75%+", "Begin AIGP study — IAPP textbook chapters 1–4", "Follow up on all pending applications — add 'AAIA exam scheduled' to messages"]
            },
        ],
    },

    // ─────────────────────────────────────────────────────────────────────────
    // POOJA CHOUBEY — Molecular Genetics & Bioinformatics
    // ─────────────────────────────────────────────────────────────────────────
    pooja: {

        // ── Career Trajectory ──────────────────────────────────────────────────
        trajectory: {
            current: { title: "Ph.D. Postdoc Scientist (Molecular Genetics)", salary: "$58K–$72K", yoe: 8 },
            target12: { title: "Scientist II / Senior Research Scientist (Biotech)", salary: "$110K–$135K", probability: 79 },
            target36: { title: "Principal Scientist / Group Leader", salary: "$145K–$175K", probability: 55 },
            north_star: { title: "Director of Research / VP R&D", salary: "$200K–$260K", probability: 32 },
            market_signal: "CRISPR therapeutics market projected +$9.8B by 2030. AI-driven drug discovery creating hybrid Bioinformatics+ML roles.",
            disruption_risk: "LOW — Experimental scientists who can speak Python are uniquely valuable. AI cannot replace wet-lab expertise.",
        },

        // ── Certification Roadmap ──────────────────────────────────────────────
        certifications: [
            {
                id: "GLP_GCP", name: "GLP/GCP Foundations Certificate", issuer: "RAPS / ACRP / NIH",
                status: "IMMEDIATE — 2 WEEKS", priority: 1, urgency: "IMMEDIATE",
                timeline: "1–2 weeks", cost: "$0–$250 (NIH free options available)", roi: "↑ 45% interview callback rate for industry QC roles",
                why: "The single biggest keyword gap vs industry peers. 'GLP' appears in 91% of Scientist II JDs at Illumina, Thermo Fisher, Amgen.",
                domains: ["ALCOA+ Data Integrity Principles", "FDA 21 CFR Part 11", "SOP Writing & Execution", "CAPA Process", "Documentation Standards", "Equipment Qualification"],
                study_hours: 15,
                pass_rate: "95% (online completion-based)",
                top_questions: [
                    "What does ALCOA+ stand for and why is each element required?",
                    "Explain FDA 21 CFR Part 11 requirements for electronic lab records.",
                    "What is a CAPA and when must one be initiated?",
                    "What is a deviation vs an out-of-specification (OOS) result?",
                    "How do you qualify a new piece of equipment under GMP?",
                ],
                resources: ["NIH GCP Training (free)", "FDA Guidance on 21 CFR Part 11", "RAPS Fundamentals of GLP/GCP", "ICH E6(R2) GCP Guidelines"],
            },
            {
                id: "ISO13485", name: "ISO 13485 Quality Management (Medical Devices)", issuer: "BSI / ASQ",
                status: "3 MONTHS", priority: 2, urgency: "SHORT",
                timeline: "4–6 weeks self-study", cost: "$350–$800", roi: "Opens $1.2T medical device sector — Illumina, Agilent, BD, Bio-Rad",
                why: "If your genomic assay touches clinical diagnostics (NGS panels, CRISPR diagnostics), ISO 13485 is mandatory compliance. Companies desperately need scientists who understand both.",
                domains: ["QMS Design & Implementation", "Design Controls for Medical Devices", "Risk Management (ISO 14971)", "CAPA & Non-Conformance", "Supplier Qualification", "Post-Market Surveillance"],
                study_hours: 60,
                pass_rate: "78% first attempt",
                top_questions: [
                    "What is the scope difference between ISO 9001 and ISO 13485?",
                    "Describe the Design History File (DHF) and what it must contain.",
                    "How does ISO 14971 risk management integrate with ISO 13485?",
                    "What are the CAPA effectiveness check requirements?",
                    "Explain the difference between IQ, OQ, and PQ validation.",
                ],
                resources: ["BSI ISO 13485 Implementation Guide", "ASQ Medical Device Quality Certificate Course", "FDA Design Control Guidance"],
            },
            {
                id: "ABMGG", name: "Board Certification in Molecular Genetics (Clinical)", issuer: "ABMGG",
                status: "12+ MONTHS", priority: 3, urgency: "LONG",
                timeline: "2 years clinical training track", cost: "$2,500 exam", roi: "Opens clinical lab director track — $140K–$185K",
                why: "If pivoting toward clinical genomics (hospital labs, genetic counseling centers), ABMGG is the gold standard credential.",
                domains: ["Clinical Cytogenetics", "Molecular Pathology", "Biochemical Genetics", "Clinical Bioinformatics", "Laboratory Management"],
                study_hours: 300,
                pass_rate: "71% first attempt",
                top_questions: [
                    "Describe the ACMG classification for variants of uncertain significance (VUS).",
                    "What is the difference between PCR, ddPCR, and qPCR in clinical diagnostics?",
                    "Explain the CAP/CLIA requirements for NGS clinical laboratory certification.",
                    "What is the analytical sensitivity vs. specificity of a clinical NGS assay?",
                    "Describe the bioinformatics pipeline from raw FASTQ to variant calling.",
                ],
                resources: ["ACMG Laboratory Standards & Guidelines", "CAP NGS Checklist", "ClinVar Database Training"],
            },
            {
                id: "ASQ_CQA", name: "ASQ Certified Quality Auditor", issuer: "ASQ",
                status: "6 MONTHS", priority: 4, urgency: "MEDIUM",
                timeline: "8–10 weeks", cost: "$468 (ASQ member)", roi: "Bridges biotech QA/QC and Lab Operations tracks",
                why: "For the hybrid Scientist + QC Auditor path at pharma (Pfizer, Merck, Novartis QA teams). Pairs perfectly with GLP/GCP.",
                domains: ["Audit Types & Purposes", "Audit Process & Tools", "Audit Reporting", "Quality Systems & Standards", "Quality Tools"],
                study_hours: 80,
                pass_rate: "61% first attempt",
                top_questions: [
                    "What is the difference between a first, second, and third-party audit?",
                    "How do you write an audit nonconformance report?",
                    "What is the purpose of an audit checklist vs. a protocol?",
                    "Describe the PDCA cycle and how it maps to ISO audit requirements.",
                    "What are the ASQ Code of Ethics obligations for a CQA?",
                ],
                resources: ["ASQ CQA Body of Knowledge", "ASQ Quality Auditing Handbook", "ISO 19011:2018 Guidelines for Auditing"],
            },
        ],

        // ── Interview Prep ─────────────────────────────────────────────────────
        interview: {
            behavioral: [
                {
                    q: "Tell me about a time you had to troubleshoot a failed experiment.",
                    star: {
                        S: "During CRISPR screen for synthetic lethality in pancreatic cancer, 40% of guides showed zero depletion — an expected edit rate of 80% was missed.",
                        T: "I needed to diagnose within 48 hours or lose $25K in cell culture and sequencing costs.",
                        A: "I systematically checked: (1) guide RNA quality via Bioanalyzer — RIN 7.2, acceptable. (2) Cas9 protein activity via T7E1 assay — no cutting activity detected. (3) Traced to a -80°C freezer failure that had partially degraded the Cas9 aliquots. Re-ordered, re-validated, re-ran.",
                        R: "Screen recovered. Published in Nature Cell Biology (2024). Established a Cas9 activity QC checkpoint that reduced downstream failures by 85%."
                    },
                    tip: "Industry wants scientists who debug methodically, not randomly. Show your diagnostic process."
                },
                {
                    q: "How do you handle working with a dry-lab bioinformatician when you disagree on the analysis approach?",
                    star: {
                        S: "Co-first-author project. I wanted DESeq2 for RNA-seq normalization; bioinformatician preferred edgeR.",
                        T: "Had to resolve the technical disagreement without damaging the collaboration.",
                        A: "I proposed running both pipelines in parallel on the same dataset and comparing the overlap of differentially expressed genes. Both methods agreed on 94% of genes. We published both results and let reviewers see both, demonstrating robustness.",
                        R: "Paper accepted without revision requests on the statistical methodology. Co-author became a long-term collaborator."
                    },
                    tip: "Biotech hiring managers love 'show me the data' problem-solving over opinion-based arguments."
                },
                {
                    q: "Tell me about your transition from academic research to industry.",
                    star: {
                        S: "Academic postdoc: freedom to explore, slow timelines, publications as currency. Industry: milestones, deadlines, revenue as currency.",
                        T: "I had to proactively retool myself for industry pace and vocabulary.",
                        A: "Completed GLP/GCP foundation certificate. Translated all CV bullet points from academic language ('investigated the role of...') to industry impact ('developed an NGS QC pipeline that reduced failed sequencing runs by 62%'). Joined Biotech-specific LinkedIn groups and RAPS community.",
                        R: "Interviewing with Illumina and Thermo Fisher within 6 weeks of targeted outreach. Three screening calls in Week 1."
                    },
                    tip: "Address the 'why industry now?' question proactively and confidently — it's always asked."
                },
            ],
            technical: [
                {
                    q: "Walk me through your NGS data analysis pipeline from raw reads to results.",
                    a: "Raw FASTQ → FastQC quality check (Q30 >80%, duplication <20%) → Trimmomatic adapter trimming → STAR/HISAT2 alignment to GRCh38 → SAMtools sort and index → featureCounts/HTSeq quantification → DESeq2/edgeR differential expression → pathway enrichment via clusterProfiler (KEGG/GO) → visualization in R ggplot2. For QC: I check RIN ≥8.0 at library prep, and run MultiQC to aggregate across all samples before proceeding."
                },
                {
                    q: "How do you ensure reproducibility in your CRISPR screens?",
                    a: "Five pillars: (1) Library validation — deep sequence guide library to verify representation (>300× coverage, Gini <0.2). (2) Cas9 activity QC — T7E1 or flow cytometry before every large screen. (3) Biological replicates — minimum n=3 independent infections. (4) MAGeCK analysis for robust gene-level statistics (use MLE not RRA for complex screens). (5) Orthogonal validation — top hits validated by 3 independent guides via individual knockout."
                },
                {
                    q: "Explain the difference between data-dependent and data-independent acquisition in proteomics, and how it compares to NGS.",
                    a: "DDA: MS selects the top N most abundant peptide precursors for fragmentation. High depth for those precursors but stochastic — different peptides selected run-to-run, poor reproducibility. DIA: All precursors within a window are co-fragmented. Reproducible quantification across all samples simultaneously. NGS analogy: DDA ≈ targeted sequencing (deep but selective); DIA ≈ WGS (comprehensive, reproducible). For biomarker discovery requiring reproducibility across patient cohorts, DIA is preferred."
                },
            ],
            salary_negotiation: {
                target_range: "$112,000 – $130,000",
                anchor: "$132,000",
                justification: ["Ph.D. + 5 years postdoc = equivalent to 7-8 years industry experience", "CRISPR + NGS + R/Python = rare triple expertise", "Publications in Nature Cell Biology = top-tier research credibility", "GLP/GCP certified = immediate compliance-ready"],
                counter_script: "Thank you for the offer. Based on published salary data for Scientist II roles with dual wet-lab and bioinformatics expertise in the Boston/SD biotech market, and given my NGS pipeline experience and GLP/GCP certification, I was targeting $128K. Is there flexibility to get closer to that range?",
                walk_away: "$105,000 base",
            },
        },

        // ── Resume Optimization ────────────────────────────────────────────────
        resume: {
            headline: "Senior Research Scientist | Molecular Genetics & Computational Genomics | CRISPR · NGS · RNA-seq · R · Python | GLP/GCP Certified",
            power_bullets: [
                "Developed genome-wide CRISPR screen (18,000 guides) identifying 47 synthetic lethal targets — published Nature Cell Biology (2024).",
                "Built automated RNA-seq QC pipeline in R/Bioconductor; reduced failed sequencing runs by 62%, saving $80K annually.",
                "Led NGS assay development for BRCA1/2 panel; achieved 99.7% sensitivity at 0.5% variant allele frequency.",
                "Collaborated with 3 bioinformatics teams across 2 institutions; delivered joint publication in 9 months vs. 18-month average.",
                "Trained 6 graduate students and 2 postdocs in CRISPR techniques; 100% retention of trainees in research careers.",
            ],
            keywords_inject: ["CRISPR/Cas9", "RNA-seq", "NGS", "Next-Generation Sequencing", "Bioinformatics", "R/Bioconductor", "Python", "GLP", "GCP", "ALCOA+", "SOP", "CAPA", "ISO 13485", "21 CFR Part 11", "DESeq2", "edgeR", "STAR aligner", "MAGeCK", "Illumina", "Flow Cytometry", "Western Blot", "qPCR", "ddPCR"],
            ats_score_tips: ["Use 'RNA-seq' AND 'RNA sequencing' — different ATS parse differently", "Add 'LIMS' as a skill even if indirect experience — in 78% of QC Scientist JDs", "Title must be 'Research Scientist' or 'Scientist II' — not 'Postdoctoral Researcher'"],
        },

        // ── LinkedIn Strategy ──────────────────────────────────────────────────
        linkedin: {
            headline: "Research Scientist | CRISPR · NGS · RNA-seq · Bioinformatics | From genome to discovery — turning biological data into therapeutic insights",
            about_hook: "I design CRISPR experiments in the morning and analyze the sequencing data in the afternoon. Rare hybrid of wet-lab precision and computational fluency — currently transitioning from academic discovery research to biotech product development.",
            content_pillars: [
                { topic: "CRISPR Technique Deep-Dives", frequency: "Bi-weekly", format: "Thread: 1 method → 5 key points" },
                { topic: "RNA-seq Tips for Biologists", frequency: "Weekly", format: "Short educational post" },
                { topic: "Academic → Industry Transition Story", frequency: "Monthly", format: "Personal narrative article" },
                { topic: "Regulatory Compliance in the Lab", frequency: "Monthly", format: "GLP/GCP practical tips post" },
            ],
            target_connections: ["Scientists at Illumina, Thermo Fisher, Amgen, Genentech", "Recruiting managers at biotech companies 50-500 employees", "RAPS association members", "Biotech LinkedIn community managers", "Former lab members now in industry"],
        },

        // ── Networking ─────────────────────────────────────────────────────────
        networking: {
            communities: [
                { name: "RAPS (Regulatory Affairs Professionals Society)", action: "Join; attend virtual GLP/GCP workshops", url: "https://www.raps.org" },
                { name: "BIO (Biotechnology Innovation Organization)", action: "Register for BIO International Convention", url: "https://www.bio.org" },
                { name: "AACR (American Association for Cancer Research)", action: "Present at annual meeting; network with Genentech/Roche scientists", url: "https://www.aacr.org" },
                { name: "LinkedIn: Bioinformatics Scientists Group", action: "Post RNA-seq tip weekly; engage with 3 posts daily", url: "https://linkedin.com/groups/bioinformatics" },
            ],
            outreach_template: "Hi [Name], I'm a CRISPR/genomics researcher at [Institution], publishing in [journal area], now exploring the transition to biotech R&D. Your work at [company] on [specific project] caught my attention — particularly [specific aspect]. Would you be open to sharing 20 minutes about the transition from academic to industry? It would mean a lot.",
        },

        // ── Market Intelligence ────────────────────────────────────────────────
        market: {
            salary_bands: [
                { role: "Scientist II (CRISPR/NGS)", range: "$108K–$135K", median: "$119K", location: "Boston / San Diego / SF Bay" },
                { role: "Senior Scientist (Bioinformatics)", range: "$130K–$155K", median: "$142K", location: "Boston / NYC / Remote" },
                { role: "Principal Scientist", range: "$155K–$180K", median: "$165K", location: "Major Biotech Hubs" },
                { role: "QC Scientist II (NGS Diagnostics)", range: "$95K–$120K", median: "$108K", location: "Broad market" },
            ],
            top_hiring: ["Illumina", "Thermo Fisher Scientific", "Genentech/Roche", "Amgen", "Pfizer Oncology", "Foundation Medicine", "Pacific Biosciences", "10x Genomics", "Cellectis", "Beam Therapeutics"],
            skills_rising: [
                { skill: "Single-Cell RNA-seq (scRNA-seq)", delta: "+285%", since: "2024" },
                { skill: "AI/ML + NGS Integration", delta: "+240%", since: "2024" },
                { skill: "CRISPR Base Editing", delta: "+195%", since: "2025" },
                { skill: "Spatial Transcriptomics", delta: "+180%", since: "2024" },
                { skill: "Long-Read Sequencing (PacBio/Oxford)", delta: "+155%", since: "2025" },
                { skill: "R + Python Dual Fluency", delta: "+140%", since: "2023" },
            ],
            jd_keywords_trend: ["CRISPR", "NGS", "RNA-seq", "single-cell", "scRNA-seq", "bioinformatics", "R/Python", "GLP", "GCP", "ALCOA+", "SOP", "CAPA", "ISO 13485", "reproducibility", "LIMS", "DESeq2", "STAR"],
            market_narrative: "The convergence of CRISPR therapeutics (Vertex/CRISPR Therapeutics's exa-cel approval), single-cell sequencing, and AI-driven drug discovery is creating unprecedented demand for scientists who bridge wet lab and computational skills. Postdocs with NGS + Python + CRISPR expertise are the most sought-after hires in biotech history. The window to command a $110–$130K Scientist II offer is now — before competition from newly minted PhDs peaks in 2027.",
        },

        // ── Study Vault ────────────────────────────────────────────────────────
        study_vault: [
            {
                id: "pj_alcoa", title: "ALCOA+ — Data Integrity Master Reference", category: "Regulatory Compliance", weight: "CRITICAL",
                icon: "📋", exam_map: ["GLP_GCP", "ISO13485", "ASQ_CQA"],
                content: [
                    { h: "ALCOA+ Full Definition", body: "A — Attributable: Each data entry identifies WHO recorded it and WHEN. Electronic systems must capture user ID and timestamp.\n\nL — Legible: Data must be readable for the full retention period. Pencil is not acceptable in GLP labs.\n\nC — Contemporaneous: Data recorded at the time of observation. No back-filling, pre-filling, or reconstruction from memory.\n\nO — Original: First captured data on the first medium. Transcribed data must reference the original source.\n\nA — Accurate: Truthful, correct, and complete record of observations and results.\n\n+ Complete: No missing data; blank fields must be explained ('N/A' + reason).\n+ Consistent: Data recorded in a consistent format (dates: DD-MMM-YYYY).\n+ Enduring: Stored on durable media for the required retention period.\n+ Available: Accessible for inspection at any time during the retention period." },
                    { h: "Common ALCOA+ Violations (GLP Audit)", body: "CRITICAL VIOLATIONS:\n• Backdating entries (fails C — Contemporaneous)\n• Using correction fluid (fails L — Legible; original data must remain readable)\n• Unsigned entries (fails A — Attributable)\n• System dates manually altered in computer (fails A + C)\n\nMINOR VIOLATIONS:\n• Dates written as MM/DD/YYYY instead of DD-MMM-YYYY (fails C — Consistent)\n• Missing unit on a measurement (fails A — Accurate)\n• Blank required field with no 'N/A' justification (fails + Complete)\n\nCORECTION PROTOCOL: Single line through error, initials, date, reason. Never erase or white-out." },
                    { h: "21 CFR Part 11 — Electronic Records", body: "Applies to: Any electronic records used to satisfy FDA requirements.\n\nKey Requirements:\n1. Access controls — unique user ID and password per person\n2. Audit trails — computer-generated, date/time stamped, operator-independent\n3. Authority checks — only authorized individuals can perform specific functions\n4. Electronic signatures — legally binding; must link signature to record\n5. Validation — system must be validated to ensure accuracy and reliability\n\nExam Trap: Part 11 applies to records in ELECTRONIC FORM that are created, modified, maintained, archived, retrieved, or transmitted under FDA requirements — not ALL electronic records in the lab." },
                ]
            },
            {
                id: "pj_ngs_qc", title: "NGS Quality Control — Complete Reference", category: "Technical Genomics", weight: "CRITICAL",
                icon: "🧬", exam_map: ["GLP_GCP", "ABMGG"],
                content: [
                    { h: "NGS QC Checkpoints", body: "PRE-SEQUENCING:\n• DNA/RNA quality: RIN ≥8.0 (RNA), A260/A280 1.8–2.0 (DNA), A260/A230 ≥1.8\n• Qubit quantification: minimum 10 ng/µL DNA; 50 ng/µL RNA for library prep\n• Fragment size: Bioanalyzer peak at 300–500 bp for WGS libraries\n\nPOST-SEQUENCING (FastQC metrics):\n• %Q30 bases: ≥80% (Illumina standard is ≥75% Q30)\n• Per-tile sequence quality: No red tiles (indicates flow cell issues)\n• Sequence duplication: <20% for WGS; <50% for amplicon sequencing\n• Adapter contamination: <1% if trimming applied\n\nALIGNMENT QC (Samtools/Picard):\n• Mapping rate: ≥95% for WGS; ≥90% for RNA-seq\n• On-target rate: ≥80% for targeted panels\n• Coverage uniformity: Mean±SD, <20% CV acceptable\n• Insert size: Distribution centered at 200–400 bp" },
                    { h: "RNA-seq Differential Expression Pipeline", body: "Step 1: Quality Check — FastQC + MultiQC report across all samples\nStep 2: Trimming — Trimmomatic (LEADING:3 TRAILING:3 SLIDINGWINDOW:4:15 MINLEN:35)\nStep 3: Alignment — STAR (splice-aware) or HISAT2 to GRCh38\nStep 4: Quantification — featureCounts or RSEM for TPM/FPKM\nStep 5: Normalization — DESeq2 uses size factors; edgeR uses TMM\nStep 6: DE Analysis — DESeq2 Wald test for simple comparisons; LRT for time-course\nStep 7: Interpretation — padj <0.05 (not raw p-value); |log2FC| ≥1.0 as effect size cutoff\nStep 8: Pathway Analysis — clusterProfiler: enrichKEGG(), enrichGO()\n\nDeseq2 vs edgeR:\n• DESeq2: Better for fewer samples (n<20), conservative\n• edgeR: Better for many samples, more powerful with good replication" },
                    { h: "CRISPR Screen Analysis (MAGeCK)", body: "Input: Paired FASTQ files (Day 0 = plasmid library; Day N = selection)\n\nMAGeCK test (RRA — Robust Rank Aggregation):\n• Identifies genes with consistent guide depletion/enrichment\n• Use for simple essential gene screens\n• Output: gene_summary.txt with pos.score and neg.score\n\nMAGeCK MLE (Maximum Likelihood Estimation):\n• Better for multi-condition comparisons\n• Provides beta scores (positive = enriched; negative = depleted)\n• Use for complex screens with multiple timepoints\n\nQuality Metrics:\n• Gini index <0.2 (guide representation, lower = better)\n• Guide mapping rate >95%\n• Control guide performance: negative controls should cluster near 0\n\nValidation: Top 10 hits confirmed by individual sgRNA knockout + Western Blot or flow cytometry phenotype" },
                ]
            },
            {
                id: "pj_crispr", title: "CRISPR/Cas9 — Mechanism, Variants & Troubleshooting", category: "Technical Genomics", weight: "HIGH",
                icon: "✂️", exam_map: ["ABMGG"],
                content: [
                    { h: "Core Mechanism", body: "1. Guide design: 20-nt protospacer + NGG PAM (SpCas9)\n   Rules: GC content 40–70%; avoid ≥4 consecutive T's (Pol III terminator)\n   Tools: Benchling, CRISPOR, CHOPCHOP for off-target scoring\n\n2. RNP delivery vs. plasmid vs. lentiviral:\n   RNP (ribonucleoprotein): Fastest (24h), lowest off-target, no integration risk\n   Plasmid: Slower, higher off-target, risk of integration (avoid for clinical)\n   Lentiviral: Best for pooled screens (stable integration needed), MOI 0.3\n\n3. Editing outcomes:\n   NHEJ → indels → frameshift → KO (disruption of ORF)\n   HDR → precise edit via donor template (requires homology arms ≥50 bp)\n   Base editing → C→T (CBE) or A→G (ABE) without DSB\n   Prime editing → flexible edits via pegRNA + RT domain" },
                    { h: "Troubleshooting Guide", body: "Low editing efficiency (<30%):\n→ Check Cas9 activity: T7E1 assay or ICE analysis (Synthego)\n→ Check guide RNA quality: Bioanalyzer (should show single band)\n→ Verify PAM is correct for your Cas variant\n→ Optimize delivery: try RNP over plasmid\n→ Check cell health: viability must be >90% before nucleofection\n\nHigh off-target cleavage:\n→ Use high-fidelity Cas9: SpCas9-HF1, eSpCas9, or HypaCas9\n→ Reduce guide/Cas9 dose (less time in nucleus)\n→ Use RNP format (rapid degradation reduces off-target window)\n→ Run GUIDE-seq or CIRCLE-seq to map off-target sites experimentally\n\nToxicity after delivery:\n→ Reduce nucleofection voltage or increase recovery time\n→ Try split delivery (Cas9 Day 0, guide Day 1)\n→ Add antioxidants (NAC) to recovery media" },
                ]
            },
            {
                id: "pj_iso13485", title: "ISO 13485 — Quality Management for Medical Devices", category: "Regulatory Compliance", weight: "HIGH",
                icon: "🏥", exam_map: ["ISO13485", "ASQ_CQA"],
                content: [
                    { h: "Key Clauses", body: "Clause 4: Quality Management System — must be documented, implemented, maintained\nClause 5: Management Responsibility — top management owns QMS; must appoint Management Representative\nClause 6: Resource Management — infrastructure, work environment, human resources\nClause 7: Product Realization — design controls, purchasing, production, service\nClause 8: Measurement, Analysis, Improvement — internal audits, CAPA, data analysis\n\nVs. ISO 9001:\n• 13485 is more prescriptive (less 'determine what's necessary')\n• 13485 requires documented procedures for specific clauses (9001 is flexible)\n• 13485 has explicit risk management hook to ISO 14971\n• 13485 does NOT require continual improvement — only maintained effectiveness" },
                    { h: "Design Controls (Clause 7.3)", body: "Design and Development Planning → Design Input → Design Output → Design Review → Design Verification → Design Validation → Design Transfer → Design Changes → Design History File (DHF)\n\nDesign Input: Requirements for intended use (what the device must do)\nDesign Output: Specifications, drawings, code (how it will do it)\nVerification: Confirms design output meets design input (does it meet spec?)\nValidation: Confirms device meets user needs under actual or simulated use (does it work for users?)\n\nDHF: The complete compilation of all design records for a device — must demonstrate compliance with the design plan.\n\nExam Trap: Verification is against specifications. Validation is against intended use. They are sequential, not interchangeable." },
                    { h: "CAPA Process", body: "Corrective Action = fix the root cause of an existing nonconformity\nPreventive Action = prevent occurrence of potential (not yet present) nonconformity\n\nCapa Steps:\n1. Identify the nonconformity or potential issue\n2. Investigate and determine root cause (5-Why, Fishbone)\n3. Define corrective/preventive actions\n4. Implement actions\n5. Verify effectiveness (typically 30–90 days post-implementation)\n6. Close CAPA with documented evidence\n\nFDA/ISO Audit Trigger: Most cited finding is 'CAPA not implemented in a timely manner' or 'effectiveness not verified'." },
                ]
            },
        ],

        // ── Weekly Action Plan ─────────────────────────────────────────────────
        action_plan: [
            {
                week: "Week 1", title: "Industry Pivot Sprint", color: "#f43f5e", priority: "CRITICAL",
                tasks: ["Complete NIH GCP online training (free, 1-2 days) — get certificate", "Rewrite resume headline: remove 'Postdoc', add 'Research Scientist | CRISPR · NGS'", "Push top RNA-seq R script to public GitHub with README", "Apply to 5 Scientist II roles: Illumina, Thermo Fisher, 10x Genomics, Foundation Medicine, Amgen"]
            },
            {
                week: "Week 2", title: "Credential & Network", color: "#f59e0b", priority: "HIGH",
                tasks: ["Register for RAPS GLP Fundamentals workshop", "Connect with 10 biotech scientists on LinkedIn — personalized notes", "Rewrite 5 CV bullets from academic → industry impact language", "Request informational interview from 2 former lab members now in industry"]
            },
            {
                week: "Week 3–4", title: "Market Penetration", color: "#6366f1", priority: "HIGH",
                tasks: ["Begin ISO 13485 self-study (BSI guide, 2 hours/day)", "Apply to 10 more roles — bring total to 15", "Publish LinkedIn post: 'What CRISPR Screen Analysis Actually Looks Like'", "Follow up on all Week 1 applications"]
            },
            {
                week: "Month 2", title: "Certification Push", color: "#10b981", priority: "MEDIUM",
                tasks: ["Complete GLP/GCP certificate (if not done)", "Begin ASQ CQA BOK review", "Attend RAPS or BIO virtual networking event", "Negotiate salary range research — target $128K for Scientist II in San Diego/Boston"]
            },
        ],
    }
};
