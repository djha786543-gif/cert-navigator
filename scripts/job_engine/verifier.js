const puppeteer = require('puppeteer');
const sqlite3 = require('sqlite3').verbose();
const path = require('path');

// Domain Isolation Rules
const DOMAIN_RULES = {
    deobrat: ["audit", "grc", "ai", "cloud", "security", "nist", "iso", "risk"],
    pooja: ["molecular", "genetics", "crispr", "rna", "qc", "laboratory", "biotech", "scientist"]
};

// Recognized ATS and Company portals
const VALID_ATS_DOMAINS = [
    "workday", "taleo", "greenhouse", "lever", "icims", "breezy", "myworkdayjobs",
    "ashbyhq", "smartrecruiters", "careers", "jobs.", "brassring", "successfactors"
];
const AGGREGATOR_DOMAINS = ["indeed", "adzuna", "ziprecruiter", "monster", "glassdoor", "linkedin", "simplyhired"];

const dbPath = path.join(__dirname, 'jobs.sqlite');
const db = new sqlite3.Database(dbPath);

async function verifyJobs() {
    console.log("[AGENT] Starting Real-Time Job Verification Subagent...");
    const browser = await puppeteer.launch({ headless: "new" });
    const page = await browser.newPage();

    db.all(`SELECT * FROM jobs_scored WHERE status = 'scored'`, async (err, jobs) => {
        if (err) { console.error(err); process.exit(1); }
        if (jobs.length === 0) {
            console.log("[AGENT] No jobs pending verification.");
            await browser.close();
            return;
        }

        for (const job of jobs) {
            console.log(`\n[AGENT] Verifying: ${job.title} at ${job.company}`);

            // 1. Strict Domain Isolation Filter (Pre-check)
            // Determine whose job this is based on keywords
            let detectedProfile = 'unknown';
            const textToAnalyze = (job.title + " " + job.description).toLowerCase();

            let deobratScore = DOMAIN_RULES.deobrat.filter(k => textToAnalyze.includes(k)).length;
            let poojaScore = DOMAIN_RULES.pooja.filter(k => textToAnalyze.includes(k)).length;

            if (deobratScore > poojaScore && deobratScore > 0) detectedProfile = 'deobrat';
            else if (poojaScore > deobratScore && poojaScore > 0) detectedProfile = 'pooja';

            // Rule: "NEVER allow Audit keywords to appear in the Pooja view."
            if (detectedProfile === 'pooja' && textToAnalyze.includes('audit')) {
                console.log(`[PURGE] VIOLATION: Audit keywords found in Science job (${job.title}). Deleting.`);
                db.run(`DELETE FROM jobs_scored WHERE id = ?`, [job.id]);
                continue;
            }

            // 2. Browser Verification (hit the ACTUAL company career portal)
            try {
                console.log(`[AGENT] Navigating to Apply URL: ${job.url}`);
                await page.goto(job.url, { waitUntil: 'domcontentloaded', timeout: 15000 });
                const finalUrl = page.url().toLowerCase();

                // Optimum Filter Definitions
                const DEOBRAT_APPROVED = ["deloitte", "pwc", "ey", "kpmg", "servicenow", "stripe", "plaid", "square", "fintech", "block"];
                const POOJA_APPROVED = ["illumina", "amgen", "thermo", "fisher", "nih.gov", "nature.com"];

                let isCompanyHosted = false;

                // Company / Target checking logic
                const companyName = job.company.toLowerCase();
                let matchesOptimum = false;
                if (detectedProfile === 'deobrat') {
                    matchesOptimum = DEOBRAT_APPROVED.some(d => companyName.includes(d) || finalUrl.includes(d));
                } else if (detectedProfile === 'pooja') {
                    matchesOptimum = POOJA_APPROVED.some(d => companyName.includes(d) || finalUrl.includes(d));
                }

                if (!matchesOptimum) {
                    console.log(`[PURGE] Discarded! Not in Optimum Filter target list for ${detectedProfile}: ${job.company}`);
                    db.run(`DELETE FROM jobs_scored WHERE id = ?`, [job.id]);
                } else if (AGGREGATOR_DOMAINS.some(d => finalUrl.includes(d) && !finalUrl.includes('careers.'))) {
                    console.log(`[PURGE] Discarded! URL resolves to generic aggregator: ${finalUrl}`);
                    db.run(`DELETE FROM jobs_scored WHERE id = ?`, [job.id]);
                } else {
                    isCompanyHosted = true;
                    console.log(`[✅ VERIFIED] Resolved to direct company portal: ${finalUrl}`);
                    db.run(`UPDATE jobs_scored SET status = 'verified_at_source', final_url = ? WHERE id = ?`, [finalUrl, job.id]);
                }
            } catch (e) {
                console.log(`[WARN] Navigation failed or timeout for ${job.title}, marking as dead link.`);
                db.run(`DELETE FROM jobs_scored WHERE id = ?`, [job.id]);
            }
        }

        console.log("\n[AGENT] Verification complete.");
        await browser.close();
        db.close();
    });
}

verifyJobs();
