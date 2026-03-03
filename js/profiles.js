const USER_PROFILES = {
    deobrat: {
        name: "Deobrat Jha",
        title: "Senior IT Audit Lead (AI & Cloud GRC)",
        RESUME_DATA: {
            hardSkills: [
                { skill: "SOX 404 / ITGC Testing", category: "Audit Core", demand: 98, years: 10, marketSignal: "🔥 Critical" },
                { skill: "AI/ML Governance", category: "Emerging", demand: 95, years: 2, marketSignal: "🔥 Critical" },
                { skill: "AWS Cloud Audit", category: "Cloud", demand: 94, years: 2, marketSignal: "🔥 Critical" },
                { skill: "NIST AI RMF", category: "Emerging", demand: 94, years: 1, marketSignal: "🔥 Critical" },
                { skill: "SAP S/4HANA Controls", category: "ERP", demand: 91, years: 8, marketSignal: "⚡ High" },
                { skill: "SOC 1 / SOC 2 Type II", category: "Assurance", demand: 90, years: 8, marketSignal: "⚡ High" },
                { skill: "Risk Assessment", category: "GRC", demand: 89, years: 10, marketSignal: "⚡ High" },
                { skill: "ISO 42001", category: "Emerging", demand: 86, years: 1, marketSignal: "⚡ High" },
                { skill: "Python / Data Analytics", category: "Technical", demand: 84, years: 3, marketSignal: "⚡ High" }
            ],
            softSkills: [
                { skill: "C-Suite Communication", evidence: "Presented findings to CFO & Audit Committee quarterly", signal: "STRONG" },
                { skill: "Team Leadership", evidence: "Led team of 8–12 at EY; managed 4 at Public Storage", signal: "STRONG" },
                { skill: "Executive Translation", evidence: "Reduced follow-up questions by 60% via plain-English findings", signal: "STRONG" }
            ],
            positioningWeaknesses: [
                { weakness: "Title gap: IT Auditor vs Manager-level target", severity: "HIGH", fix: "Emphasize 'Led team of 4' and 'Audit Committee presenter'" },
                { weakness: "Career gap (Aug 2024–Jun 2025)", severity: "HIGH", fix: "Add: 'Active Professional Development (AAIA/AIGP)'" }
            ]
        },
        GAP_DATA: [
            { gap: "No visible AI audit portfolio / deliverable", category: "immediate", blockSeverity: 9, marketDemand: 10, roi: 10, timeToImpact: 3, action: "Add AAIA in-progress cert to resume headline. 3 days.", certLink: "AAIA" },
            { gap: "Missing AIGP certification (EU AI Act demand)", category: "short", blockSeverity: 7, marketDemand: 10, roi: 10, timeToImpact: 30, action: "Register IAPP AIGP. Begin 4-week study plan.", certLink: "AIGP" }
        ],
        EXEC_TIMELINE: [
            { phase: "Week 1–2", label: "Immediate Fixes", color: "#f43f5e", tasks: ["Add 'No sponsorship required (EAD)' to header", "Add AAIA In-Progress to certifications", "Publish LinkedIn Article: 'Auditing AI with NIST AI RMF'"] },
            { phase: "Week 3–4", label: "Short-Term Upgrades", color: "#f59e0b", tasks: ["Register for IAPP AIGP exam", "Apply to 15 scored roles", "Complete AAIA Modules 4–6"] }
        ],
        INTERVIEW_OPTIMIZER: [
            { action: "Resume keyword alignment to JD", impact: 92, effort: "Low", timeframe: "Day 1", blocker: false },
            { action: "AAIA cert listed as In-Progress", impact: 88, effort: "Low", timeframe: "Day 1", blocker: false }
        ],
        JOB_ENGINE_DATA: {
            apis: [
                { name: "Indeed Publisher API", tier: "⭐ RECOMMENDED", cost: "Free/CPA", reliability: 95, grcCoverage: 92, pros: ["Largest index", "GRC deep"], cons: ["Publisher approval"], score: 94 },
                { name: "Adzuna API", tier: "⭐ BEST VALUE", cost: "Free 10k/mo", reliability: 88, grcCoverage: 85, pros: ["Instant access", "Salary data"], cons: ["Smaller index"], score: 87 }
            ],
            scoringFactors: [
                { factor: "Title Alignment", weight: 25, description: "Target: IT Audit Manager, GRC Manager, AI Audit Lead", logic: "Exact=25pts, Partial=15pts" },
                { factor: "AI/ML Governance", weight: 18, description: "Target: AI governance, NIST AI RMF, LLM", logic: "≥3 keywords=18pts" },
                { factor: "Salary Band", weight: 15, description: "Target: $120k–$165k", logic: "Within band=15pts" }
            ],
            archLayers: [
                { layer: "Layer 1: Data Ingest", icon: "📡", color: "#6366f1", desc: "Fetch via Adzuna API", tech: "Python requests" },
                { layer: "Layer 2: Scoring", icon: "⚖️", color: "#f59e0b", desc: "7-factor weighted score", tech: "SQLite + Python" }
            ],
            automationSteps: [
                { step: 1, name: "Fetch Jobs", detail: "Cron triggers at 7AM. Query: 'IT Audit Manager AI'", code: "python job_fetcher.py" },
                { step: 2, name: "Verify at Source", detail: "Use integrated browser subagent", code: "playwright run verify.spec.ts" }
            ],
            techStack: [
                { layer: "Runtime", tech: "Python 3.11", reason: "Standard for automation" },
                { layer: "Verification", tech: "Playwright Subagent", reason: "Avoid fake aggregates" }
            ],
            optimizationEngine: [
                { metric: "Application Rate", formula: "Applications / Jobs ≥70", target: "≥5/week", action: "Lower threshold if slow" }
            ]
        },
        jobs: [
            { id: "dj1", title: "AI Risk Governance Lead", company: "FinTech Innovate", applyUrl: "https://example.com", score: 94, verified: true, source: "Direct", status: "Verified on Career Portal" },
            { id: "dj2", title: "IT Audit Manager - Cloud", company: "TechGlobal Solutions", applyUrl: "https://example.com", score: 88, verified: true, source: "Direct", status: "Verified on Career Portal" }
        ]
    },

    pooja: {
        name: "Pooja Choubey",
        title: "Ph.D. Postdoc Scientist (Molecular Genetics)",
        RESUME_DATA: {
            hardSkills: [
                { skill: "CRISPR/Cas9 Screening", category: "Core Genetics", demand: 98, years: 5, marketSignal: "🔥 Critical" },
                { skill: "RNA-seq Data Analysis", category: "Bioinformatics", demand: 95, years: 3, marketSignal: "🔥 Critical" },
                { skill: "R / Bioconductor", category: "Bioinformatics", demand: 94, years: 4, marketSignal: "🔥 Critical" },
                { skill: "Next-Generation Sequencing (NGS)", category: "Core Genetics", demand: 92, years: 6, marketSignal: "⚡ High" },
                { skill: "GLP / GCP Compliance", category: "Industry QC", demand: 89, years: 1, marketSignal: "📈 Growing" },
                { skill: "ISO 13485 (Medical Devices)", category: "Industry QC", demand: 86, years: 1, marketSignal: "📈 Growing" },
                { skill: "Cell Culture & Assays", category: "Wet Lab", demand: 85, years: 8, marketSignal: "Baseline" }
            ],
            softSkills: [
                { skill: "Cross-Disciplinary Research", evidence: "Led collaboration between dry-lab bioinformaticians and wet-lab scientists", signal: "STRONG" },
                { skill: "Grant Writing & Publication", evidence: "Author on 4 high-impact journals", signal: "STRONG" },
                { skill: "Experimental Design", evidence: "Designed large-scale CRISPR screens from target selection to validation", signal: "STRONG" }
            ],
            positioningWeaknesses: [
                { weakness: "Academic phrasing ('Postdoc') instead of industry titles ('Scientist II' / 'QC Lead')", severity: "HIGH", fix: "Reposition headline to 'Senior Scientist - Molecular Biology & Bioinformatics'" },
                { weakness: "Lack of explicit QA/QC industry vocabulary", severity: "HIGH", fix: "Add SOP drafting, CAPA, and ALCOA+ terminology to relevant lab experiences" }
            ]
        },
        GAP_DATA: [
            { gap: "No industry QA/QC credentials", category: "immediate", blockSeverity: 9, marketDemand: 10, roi: 10, timeToImpact: 3, action: "Add 'GLP/GCP Foundations' cert/training to resume. 3 days.", certLink: "GLP/GCP" },
            { gap: "Bioinformatics repo not public", category: "short", blockSeverity: 7, marketDemand: 8, roi: 9, timeToImpact: 14, action: "Push RNA-seq R scripts to public GitHub and link on resume.", certLink: "GitHub" }
        ],
        EXEC_TIMELINE: [
            { phase: "Week 1–2", label: "Industry Reposition", color: "#f43f5e", tasks: ["Translate CV to 2-page Industry Resume", "Replace 'Postdoc' with 'Research Scientist'", "Highlight RNA-seq & Python/R"] },
            { phase: "Week 3–4", label: "QC Transition Prep", color: "#f59e0b", tasks: ["Complete GLP/GCP crash course", "Apply to Biotech Hubs (Boston/SD/SF hybrid)"] }
        ],
        INTERVIEW_OPTIMIZER: [
            { action: "Resume translated to Industry format", impact: 95, effort: "Medium", timeframe: "Day 1-2", blocker: true },
            { action: "Highlighting NGS / QA instrumentation", impact: 88, effort: "Low", timeframe: "Day 3", blocker: false }
        ],
        JOB_ENGINE_DATA: {
            apis: [
                { name: "Nature Jobs / Science Boards", tier: "⭐ RECOMMENDED", cost: "Free Web Scraping", reliability: 92, grcCoverage: 95, pros: ["High biotech signal", "Pre-vetted R&D roles"], cons: ["Scraping required"], score: 91 },
                { name: "Adzuna API (Biotech Filter)", tier: "⭐ BEST VALUE", cost: "Free 10k/mo", reliability: 88, grcCoverage: 80, pros: ["Salary transparency"], cons: ["Broad index"], score: 85 }
            ],
            scoringFactors: [
                { factor: "Title Alignment", weight: 25, description: "Target: Scientist II, Bioinformatics Scientist, QC Lead", logic: "Exact=25pts, Postdoc=5pts" },
                { factor: "Core Wet Lab / Dry Lab", weight: 18, description: "Target: CRISPR, NGS, RNA-seq, R, Python", logic: "≥4 keywords=18pts" },
                { factor: "Industry/QA Signals", weight: 15, description: "Target: GLP, FDA, GMP, LIMS", logic: "Has QC/QA buzzwords=15pts" }
            ],
            archLayers: [
                { layer: "Layer 1: Biotech Ingest", icon: "🧬", color: "#ec4899", desc: "Scrape NatureCareers", tech: "Puppeteer / Playwright" },
                { layer: "Layer 2: Scoring", icon: "⚖️", color: "#f59e0b", desc: "Match R/Python & CRISPR", tech: "SQLite + Python" }
            ],
            automationSteps: [
                { step: 1, name: "Fetch R&D Jobs", detail: "Cron triggers at 8AM. Query: 'Bioinformatics Scientist CRISPR'", code: "node scrape_nature.js" },
                { step: 2, name: "Verify at Source", detail: "Verify workday/taleo portals", code: "playwright run verify_pharma.spec.ts" }
            ],
            techStack: [
                { layer: "Scraping", tech: "Playwright", reason: "Handles complex Workday/Taleo portals common in Pharma" },
                { layer: "Matching", tech: "Python NLP", reason: "Parse complex biological jargon" }
            ],
            optimizationEngine: [
                { metric: "Industry Interview Rate", formula: "Interviews / Apps", target: "≥20%", action: "Purge 'academic' words if failing" }
            ]
        },
        jobs: [
            { id: "pj1", title: "Senior CRISPR Researcher", company: "Illumina Genomics", applyUrl: "https://example.com", score: 96, verified: true, source: "Nature Jobs", status: "Verified on Career Portal" },
            { id: "pj2", title: "Director of RNA-seq Analysis", company: "Thermo Fisher", applyUrl: "https://example.com", score: 92, verified: true, source: "Science Boards API", status: "Verified on Career Portal" },
            { id: "pj3", title: "QC Scientist II", company: "Amgen", applyUrl: "https://example.com", score: 89, verified: true, source: "Direct Integration", status: "Verified on Career Portal" }
        ]
    }
};
