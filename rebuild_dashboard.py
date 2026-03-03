import re

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# ─────────────────────────────────────────────────────────────────────────────
# 1. Replace the entire view-dashboard section
# ─────────────────────────────────────────────────────────────────────────────
NEW_DASHBOARD = '''        <!-- ============ DASHBOARD VIEW — Career Navigator Gold Standard ============ -->
        <section class="view active" id="view-dashboard">

            <!-- Profile hero bar -->
            <div class="view-header" style="margin-bottom:20px">
                <div>
                    <h1 class="view-title" id="dashboardTitle">Career <span class="gradient-text">Navigator</span></h1>
                    <p class="view-subtitle" id="dashboardSubtitle">Resilience-Linked Career Engine</p>
                </div>
                <div id="dashboardBadges" class="header-badges"></div>
            </div>

            <!-- Stat Cards Row (populated by renderCareerDashboard) -->
            <div id="profileStatCards" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:14px;margin-bottom:24px"></div>

            <!-- Inner tab strip -->
            <div style="display:flex;gap:4px;border-bottom:1px solid rgba(99,102,241,0.15);margin-bottom:20px;overflow-x:auto;padding-bottom:0">
                <button class="dash-tab" id="dtbtn-jobs" onclick="switchDashTab(\'jobs\')" style="padding:8px 18px;border:none;cursor:pointer;font-size:13px;font-weight:600;border-radius:8px 8px 0 0;background:rgba(18,19,31,0.75);color:#e8e9f3;border-bottom:2px solid #6366f1;white-space:nowrap;transition:all .2s;margin-bottom:-1px">Jobs</button>
                <button class="dash-tab" id="dtbtn-intel" onclick="switchDashTab(\'intel\')" style="padding:8px 18px;border:none;cursor:pointer;font-size:13px;font-weight:600;border-radius:8px 8px 0 0;background:transparent;color:#9ca3b8;border-bottom:2px solid transparent;white-space:nowrap;transition:all .2s;margin-bottom:-1px">Market Intelligence</button>
                <button class="dash-tab" id="dtbtn-certs" onclick="switchDashTab(\'certs\')" style="padding:8px 18px;border:none;cursor:pointer;font-size:13px;font-weight:600;border-radius:8px 8px 0 0;background:transparent;color:#9ca3b8;border-bottom:2px solid transparent;white-space:nowrap;transition:all .2s;margin-bottom:-1px">Certifications</button>
                <button class="dash-tab" id="dtbtn-roadmap" onclick="switchDashTab(\'roadmap\')" style="padding:8px 18px;border:none;cursor:pointer;font-size:13px;font-weight:600;border-radius:8px 8px 0 0;background:transparent;color:#9ca3b8;border-bottom:2px solid transparent;white-space:nowrap;transition:all .2s;margin-bottom:-1px">Disruption Roadmap</button>
                <button class="dash-tab" id="dtbtn-certlab" onclick="switchDashTab(\'certlab\')" style="padding:8px 18px;border:none;cursor:pointer;font-size:13px;font-weight:600;border-radius:8px 8px 0 0;background:transparent;color:#a855f7;border-bottom:2px solid transparent;white-space:nowrap;transition:all .2s;margin-bottom:-1px">CertLab Prep</button>
            </div>

            <!-- ── JOBS PANE ── -->
            <div id="dtab-jobs" class="dtab-pane">
                <div style="display:grid;grid-template-columns:1fr 280px;gap:20px">
                    <div>
                        <div class="glass-card" style="margin-bottom:16px;overflow:hidden;border-color:rgba(99,102,241,0.22)">
                            <div style="padding:12px 16px;display:flex;align-items:center;gap:10px;border-bottom:1px solid rgba(99,102,241,0.12)">
                                <span style="padding:2px 10px;border-radius:20px;font-size:10px;font-weight:800;background:rgba(99,102,241,0.18);color:#6366f1;border:1px solid rgba(99,102,241,0.4)">TOP MATCHES TODAY</span>
                                <span style="font-size:14px;font-weight:700;color:#e8e9f3">Priority Tray</span>
                            </div>
                            <div id="priorityTrayJobs" style="padding:12px"></div>
                        </div>
                        <div id="fullJobList"></div>
                    </div>
                    <div>
                        <div style="font-size:11px;font-weight:700;color:#e8e9f3;margin-bottom:10px;text-transform:uppercase;letter-spacing:.06em">Trending Roles</div>
                        <div id="trendingRolesPanel"></div>
                        <div style="margin-top:20px;font-size:11px;font-weight:700;color:#e8e9f3;margin-bottom:10px;text-transform:uppercase;letter-spacing:.06em">Fill-Gap Priorities</div>
                        <div id="gapPriorityPanel"></div>
                    </div>
                </div>
            </div>

            <!-- ── MARKET INTEL PANE ── -->
            <div id="dtab-intel" class="dtab-pane" style="display:none">
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">
                    <div class="glass-card" style="padding:20px 24px;grid-column:1/-1">
                        <div style="font-size:11px;color:#6366f1;text-transform:uppercase;letter-spacing:.08em;margin-bottom:14px;font-weight:700">Hard Skills Matrix — Market Demand × Tenure</div>
                        <div id="skillsMatrixPanel"></div>
                    </div>
                    <div class="glass-card" style="padding:20px 24px">
                        <div style="font-size:13px;font-weight:700;color:#e8e9f3;margin-bottom:14px">⚠️ Positioning Weaknesses</div>
                        <div id="weaknessesPanel"></div>
                    </div>
                    <div class="glass-card" style="padding:20px 24px">
                        <div style="font-size:13px;font-weight:700;color:#e8e9f3;margin-bottom:14px">⚡ Interview Optimizer</div>
                        <div id="interviewOptimizerPanel"></div>
                    </div>
                </div>
            </div>

            <!-- ── CERTS PANE ── -->
            <div id="dtab-certs" class="dtab-pane" style="display:none">
                <div class="glass-card" style="padding:20px 24px">
                    <div style="font-size:13px;font-weight:700;color:#e8e9f3;margin-bottom:16px">Gap-to-Cert Action Plan</div>
                    <div id="certGapPlanPanel"></div>
                </div>
            </div>

            <!-- ── DISRUPTION ROADMAP PANE ── -->
            <div id="dtab-roadmap" class="dtab-pane" style="display:none">
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">
                    <div class="glass-card" style="padding:20px 24px;grid-column:1/-1">
                        <div style="font-size:13px;font-weight:700;color:#e8e9f3;margin-bottom:16px">🗓️ Executive 90-Day Timeline</div>
                        <div id="execTimelinePanel"></div>
                    </div>
                    <div class="glass-card" style="padding:20px 24px">
                        <div style="font-size:13px;font-weight:700;color:#e8e9f3;margin-bottom:14px">Job Engine Architecture</div>
                        <div id="jobEngineArchPanel"></div>
                    </div>
                    <div class="glass-card" style="padding:20px 24px">
                        <div style="font-size:13px;font-weight:700;color:#e8e9f3;margin-bottom:14px">Scoring Factors</div>
                        <div id="scoringFactorsPanel"></div>
                    </div>
                </div>
            </div>

            <!-- ── CERTLAB PREP PANE (original study tool content) ── -->
            <div id="dtab-certlab" class="dtab-pane" style="display:none">
                <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:14px;margin-bottom:24px">
                    <div class="stat-card"><div class="stat-icon" style="--accent:#6366f1"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg></div><div class="stat-info"><span class="stat-value">10</span><span class="stat-label">Learning Modules</span></div></div>
                    <div class="stat-card"><div class="stat-icon" style="--accent:#06b6d4"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 3v6l-3 9h12l-3-9V3"/><path d="M8 3h8"/></svg></div><div class="stat-info"><span class="stat-value">30+</span><span class="stat-label">Hands-On Labs</span></div></div>
                    <div class="stat-card"><div class="stat-icon" style="--accent:#f59e0b"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M9 9c0-1.7 1.3-3 3-3s3 1.3 3 3-1.3 3-3 3v2"/><circle cx="12" cy="18" r="0.5" fill="currentColor"/></svg></div><div class="stat-info"><span class="stat-value">200+</span><span class="stat-label">Exam Questions</span></div></div>
                    <div class="stat-card"><div class="stat-icon" style="--accent:#10b981"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg></div><div class="stat-info"><span class="stat-value" id="currentScore">0%</span><span class="stat-label">Exam Readiness</span></div></div>
                </div>
                <div class="dashboard-grid">
                    <div class="glass-card readiness-card"><h2 class="card-title">Exam Readiness Radar</h2><p class="card-desc">Domain-level proficiency across both certifications</p><canvas id="radarChart" width="400" height="300"></canvas><div class="readiness-legend" id="readinessLegend"></div></div>
                    <div class="glass-card roadmap-card"><h2 class="card-title">Learning Roadmap</h2><p class="card-desc">Recommended study path for &gt;90% readiness</p><div class="roadmap-timeline" id="roadmapTimeline"></div></div>
                </div>
                <div class="glass-card weakness-card" id="weaknessCard" style="display:none;margin-top:16px"><h2 class="card-title">🎯 Predictive Exam Analytics</h2><p class="card-desc">AI-powered weakness analysis based on your answer patterns</p><div id="predictedScorePanel" style="margin:16px 0"></div><div id="weakDomainsList"></div><div id="weakTopicsList" style="margin-top:16px"></div><div id="recommendations" style="margin-top:16px"></div></div>
                <div class="glass-card cert-comparison" style="margin-top:16px"><h2 class="card-title">Certification Overview</h2><div class="cert-grid"><div class="cert-panel aaia-panel"><div class="cert-header"><span class="cert-badge">AAIA</span><h3>Associate AI Auditor</h3></div><div class="cert-domains" id="aaiaDomains"></div></div><div class="cert-panel ciasp-panel"><div class="cert-header"><span class="cert-badge ciasp">CIASP</span><h3>Certified Information Assurance Security Professional</h3></div><div class="cert-domains" id="ciaspDomains"></div></div></div></div>
            </div>

        </section>'''

# ─────────────────────────────────────────────────────────────────────────────
# 2. Find and replace the old section.
#    We anchor on the comment + section opening, and end at the closing </section>
#    that comes right before <!-- ============ MODULES VIEW ============ -->
# ─────────────────────────────────────────────────────────────────────────────
pattern = re.compile(
    r'<!-- ============ DASHBOARD VIEW ============ -->.*?</section>(?=\s*\n\s*<!-- ============ MODULES VIEW)',
    re.DOTALL)

new_html, n = pattern.subn(NEW_DASHBOARD, html)
if n == 0:
    print("ERROR: Dashboard section not found — check anchors")
    exit(1)
print(f"Replaced {n} dashboard section(s)")

# ─────────────────────────────────────────────────────────────────────────────
# 3. Inject dashboard rendering JS before </body>
# ─────────────────────────────────────────────────────────────────────────────
RENDER_JS = '''
<script>
// ════════════════════════════════════════════════════════════════════════════
// Career Navigator Dashboard — Gold Standard Render Engine
// Ports Railway production dashboard.jsx → pure vanilla JS + USER_PROFILES data
// ════════════════════════════════════════════════════════════════════════════

// ── Colour tokens (match Railway exactly) ──────────────────────────────────
const CN = {
    indigo: "#6366f1", cyan: "#06b6d4", purple: "#a855f7",
    amber: "#f59e0b", emerald: "#10b981", rose: "#f43f5e",
    textPrimary: "#e8e9f3", textSec: "#9ca3b8", textMuted: "#5f6580",
    bgGlass: "rgba(18,19,31,0.75)", bgTertiary: "#1a1b2e",
    borderSub: "rgba(99,102,241,0.12)", borderMed: "rgba(99,102,241,0.25)"
};

const glassStyle = `background:${CN.bgGlass};backdrop-filter:blur(12px);border:1px solid ${CN.borderSub};border-radius:12px;`;

// ── Active dash profile (mirrors currentProfile global) ───────────────────
function getActiveDashProfile() {
    const id = (typeof currentProfile !== "undefined") ? currentProfile : "deobrat";
    return (typeof USER_PROFILES !== "undefined" && USER_PROFILES[id]) ? USER_PROFILES[id] : null;
}

// ── Inner dashboard tab switch ─────────────────────────────────────────────
function switchDashTab(tab) {
    document.querySelectorAll(".dtab-pane").forEach(p => p.style.display = "none");
    const pane = document.getElementById("dtab-" + tab);
    if (pane) pane.style.display = "";

    document.querySelectorAll(".dash-tab").forEach(btn => {
        const isActive = btn.id === "dtbtn-" + tab;
        btn.style.background = isActive ? CN.bgGlass : "transparent";
        btn.style.color = isActive ? CN.textPrimary : (tab === "certlab" && btn.id === "dtbtn-certlab" ? CN.purple : CN.textSec);
        btn.style.borderBottom = isActive ? `2px solid ${CN.indigo}` : "2px solid transparent";
    });

    // Lazy render on first visit
    if (tab === "intel")    renderIntelPane();
    if (tab === "certs")    renderCertsPane();
    if (tab === "roadmap")  renderRoadmapPane();
    if (tab === "certlab") { try { renderDashboard(); } catch(e){} }
}

// ── Main function called on profile switch ─────────────────────────────────
function renderCareerDashboard() {
    const profile = getActiveDashProfile();
    if (!profile) return;

    // Update header
    const titleEl = document.getElementById("dashboardTitle");
    if (titleEl) titleEl.innerHTML = `${profile.name}\'s <span class="gradient-text">Career Intel</span>`;
    const subEl = document.getElementById("dashboardSubtitle");
    if (subEl) subEl.textContent = profile.title;

    // Badges
    const badgesEl = document.getElementById("dashboardBadges");
    if (badgesEl) {
        const rData = profile.RESUME_DATA;
        const topSignal = rData?.hardSkills?.[0]?.marketSignal || "";
        badgesEl.innerHTML = `
            <span class="badge badge-aaia">${topSignal}</span>
            <span class="badge badge-ciasp">${profile.jobs?.length || 0} Jobs Verified</span>
        `;
    }

    renderStatCards(profile);
    renderJobsPane(profile);
    renderTrendingRoles(profile);
    renderGapPriorities(profile);

    // Reset to jobs tab
    switchDashTab("jobs");
}

// ── Stat Cards ─────────────────────────────────────────────────────────────
function renderStatCards(profile) {
    const el = document.getElementById("profileStatCards");
    if (!el) return;

    const topSkill = profile.RESUME_DATA?.hardSkills?.[0];
    const topGap = profile.GAP_DATA?.[0];
    const jobCount = (profile.jobs || []).length;
    const verifiedCount = (profile.jobs || []).filter(j => j.verified).length;

    const cards = [
        { icon: "👤", label: "Current Title",      value: profile.title.split(" (")[0],         accent: CN.indigo },
        { icon: "🔥", label: "Top Skill Demand",   value: topSkill ? `${topSkill.demand}%` : "—", accent: CN.cyan },
        { icon: "💼", label: "Jobs Matched",        value: jobCount,                              accent: CN.emerald },
        { icon: "✅", label: "Verified Direct",     value: verifiedCount,                         accent: CN.amber },
        { icon: "⚠️", label: "Critical Gap",        value: topGap ? `Block ${topGap.blockSeverity}/10` : "None", accent: CN.rose },
        { icon: "📈", label: "Max Market ROI",      value: topGap ? `${topGap.roi}/10` : "—",    accent: CN.purple },
    ];

    el.innerHTML = cards.map(c => `
        <div style="${glassStyle}padding:16px 18px;display:flex;align-items:center;gap:14px;transition:all .3s;cursor:default"
             onmouseover="this.style.borderColor=\'${c.accent}\';this.style.boxShadow=\'0 0 20px ${c.accent}22\'"
             onmouseout="this.style.borderColor=\'${CN.borderSub}\';this.style.boxShadow=\'none\'">
            <div style="width:44px;height:44px;border-radius:10px;background:${c.accent}18;display:flex;align-items:center;justify-content:center;font-size:20px;flex-shrink:0">${c.icon}</div>
            <div>
                <div style="font-size:18px;font-weight:800;color:${c.accent};line-height:1">${c.value}</div>
                <div style="font-size:11px;color:${CN.textMuted};margin-top:3px">${c.label}</div>
            </div>
        </div>`).join("");
}

// ── Jobs Pane ──────────────────────────────────────────────────────────────
function renderJobsPane(profile) {
    const jobs = profile.jobs || [];

    // Priority Tray
    const tray = document.getElementById("priorityTrayJobs");
    if (tray) {
        if (!jobs.length) {
            tray.innerHTML = `<div style="padding:20px;text-align:center;color:${CN.textMuted};font-size:13px">No verified jobs in this profile yet.</div>`;
        } else {
            tray.innerHTML = jobs.map(j => `
                <div style="display:flex;align-items:center;gap:12px;padding:10px 8px;border-bottom:1px solid ${CN.borderSub};transition:background .2s;border-radius:8px"
                     onmouseover="this.style.background=\'rgba(99,102,241,0.07)\'" onmouseout="this.style.background=\'transparent\'">
                    <div style="width:36px;height:36px;border-radius:8px;background:linear-gradient(135deg,${CN.indigo},${CN.cyan});display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:800;color:#fff;flex-shrink:0">${j.score}</div>
                    <div style="flex:1;min-width:0">
                        <div style="font-size:13px;font-weight:700;color:${CN.textPrimary};white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${j.title}</div>
                        <div style="font-size:11px;color:${CN.textMuted}">${j.company} · ${j.source}</div>
                    </div>
                    <div style="display:flex;align-items:center;gap:6px;flex-shrink:0">
                        <span style="padding:2px 8px;border-radius:10px;font-size:9px;font-weight:700;background:${CN.emerald}18;color:${CN.emerald};border:1px solid ${CN.emerald}40">${j.verified ? "VERIFIED" : "PENDING"}</span>
                        <a href="${j.applyUrl}" target="_blank" rel="noopener"
                           style="padding:5px 12px;border-radius:7px;background:linear-gradient(135deg,${CN.indigo},${CN.cyan});color:#fff;text-decoration:none;font-size:11px;font-weight:700;white-space:nowrap">Apply ↗</a>
                    </div>
                </div>`).join("");
        }
    }

    // Full job list (cards)
    const full = document.getElementById("fullJobList");
    if (full) {
        full.innerHTML = jobs.length === 0 ? "" : jobs.map(j => `
            <div style="${glassStyle}padding:16px 20px;margin-bottom:10px;display:flex;align-items:center;gap:16px;transition:all .2s"
                 onmouseover="this.style.borderColor=\'${CN.borderMed}\'" onmouseout="this.style.borderColor=\'${CN.borderSub}\'">
                <div style="width:48px;height:48px;border-radius:10px;background:linear-gradient(135deg,${CN.indigo}33,${CN.cyan}33);display:flex;align-items:center;justify-content:center;font-size:14px;font-weight:800;color:${CN.indigo};flex-shrink:0">${j.score}</div>
                <div style="flex:1;min-width:0">
                    <div style="font-size:14px;font-weight:700;color:${CN.textPrimary}">${j.title}</div>
                    <div style="font-size:12px;color:${CN.textSec};margin-top:2px">${j.company}</div>
                    <div style="font-size:11px;color:${CN.textMuted};margin-top:4px">${j.status}</div>
                </div>
                <div style="display:flex;flex-direction:column;align-items:flex-end;gap:8px;flex-shrink:0">
                    <span style="padding:3px 10px;border-radius:12px;font-size:10px;font-weight:700;background:${j.verified ? CN.emerald + "18" : CN.amber + "18"};color:${j.verified ? CN.emerald : CN.amber};border:1px solid ${j.verified ? CN.emerald + "40" : CN.amber + "40"}">${j.source}</span>
                    <a href="${j.applyUrl}" target="_blank" rel="noopener"
                       style="padding:6px 16px;border-radius:8px;background:transparent;color:${CN.indigo};border:1px solid ${CN.borderMed};text-decoration:none;font-size:12px;font-weight:700">Apply at Source ↗</a>
                </div>
            </div>`).join("");
    }
}

// ── Trending Roles sidebar ─────────────────────────────────────────────────
const TRENDING_DEOBRAT = [
    { role: "AI Risk & Compliance Lead",       change: "+42%", hot: true },
    { role: "IT Audit Manager — Cloud",        change: "+31%", hot: true },
    { role: "NIST AI RMF Lead",                change: "+28%", hot: false },
    { role: "GRC Manager — Fintech",           change: "+19%", hot: false },
    { role: "SOC 2 Audit Director",            change: "+14%", hot: false },
];
const TRENDING_POOJA = [
    { role: "CRISPR Genomics Scientist",       change: "+39%", hot: true },
    { role: "Bioinformatics Scientist II",     change: "+34%", hot: true },
    { role: "RNA-seq Pipeline Lead",           change: "+27%", hot: false },
    { role: "QC Scientist — NGS",              change: "+21%", hot: false },
    { role: "Computational Biology Lead",      change: "+17%", hot: false },
];

function renderTrendingRoles(profile) {
    const el = document.getElementById("trendingRolesPanel");
    if (!el) return;
    const isPooja = (typeof currentProfile !== "undefined") && currentProfile === "pooja";
    const trends = isPooja ? TRENDING_POOJA : TRENDING_DEOBRAT;
    el.innerHTML = trends.map((r, i) => `
        <div style="${glassStyle}padding:10px 14px;margin-bottom:8px;display:flex;align-items:center;justify-content:space-between">
            <div style="display:flex;align-items:center;gap:8px">
                <div style="width:22px;height:22px;border-radius:6px;background:rgba(99,102,241,0.12);display:flex;align-items:center;justify-content:center;font-size:10px;font-weight:700;color:${CN.indigo}">${i+1}</div>
                <div style="font-size:12px;color:${CN.textSec};max-width:140px;line-height:1.3">${r.role}</div>
            </div>
            <div style="display:flex;flex-direction:column;align-items:flex-end;gap:2px">
                <span style="font-size:11px;font-weight:700;color:${CN.emerald}">${r.change}</span>
                ${r.hot ? `<span style="font-size:8px;font-weight:800;color:${CN.rose}">🔥 HOT</span>` : ""}
            </div>
        </div>`).join("");
}

// ── Gap Priorities ─────────────────────────────────────────────────────────
function renderGapPriorities(profile) {
    const el = document.getElementById("gapPriorityPanel");
    if (!el) return;
    const gaps = profile.GAP_DATA || [];
    el.innerHTML = gaps.slice(0, 3).map(g => `
        <div style="${glassStyle}padding:10px 14px;margin-bottom:8px;border-left:3px solid ${g.blockSeverity >= 8 ? CN.rose : CN.amber}">
            <div style="font-size:11px;font-weight:700;color:${g.blockSeverity >= 8 ? CN.rose : CN.amber};margin-bottom:4px;text-transform:uppercase">Block ${g.blockSeverity}/10 · ROI ${g.roi}/10</div>
            <div style="font-size:12px;color:${CN.textPrimary};margin-bottom:4px;font-weight:600">${g.gap}</div>
            <div style="font-size:11px;color:${CN.textMuted}">${g.action}</div>
        </div>`).join("");
}

// ── Market Intel Pane (lazy) ───────────────────────────────────────────────
let _intelRendered = false;
function renderIntelPane() {
    if (_intelRendered) return;
    _intelRendered = false; // always refresh on profile switch
    const profile = getActiveDashProfile();
    if (!profile) return;

    const skills = profile.RESUME_DATA?.hardSkills || [];
    const mx = document.getElementById("skillsMatrixPanel");
    if (mx) {
        mx.innerHTML = skills.map(s => `
            <div style="display:flex;align-items:center;gap:12px;padding:8px 0;border-bottom:1px solid ${CN.borderSub}">
                <div style="min-width:0;flex:1">
                    <div style="display:flex;justify-content:space-between;margin-bottom:4px">
                        <span style="font-size:12px;font-weight:600;color:${CN.textPrimary}">${s.skill}</span>
                        <span style="font-size:11px;color:${CN.textMuted}">${s.years}y · ${s.category}</span>
                    </div>
                    <div style="height:6px;background:rgba(255,255,255,0.06);border-radius:3px;overflow:hidden">
                        <div style="height:100%;width:${s.demand}%;background:linear-gradient(90deg,${CN.indigo},${CN.cyan});border-radius:3px;transition:width .8s ease"></div>
                    </div>
                </div>
                <span style="font-size:11px;font-weight:700;color:${s.demand >= 90 ? CN.rose : s.demand >= 80 ? CN.amber : CN.emerald};flex-shrink:0;min-width:36px;text-align:right">${s.demand}%</span>
                <span style="font-size:10px;white-space:nowrap;color:${CN.textMuted}">${s.marketSignal}</span>
            </div>`).join("");
    }

    const weaknesses = profile.RESUME_DATA?.positioningWeaknesses || [];
    const wp = document.getElementById("weaknessesPanel");
    if (wp) {
        wp.innerHTML = weaknesses.map(w => `
            <div style="padding:10px 14px;margin-bottom:8px;border-radius:8px;background:${w.severity === "HIGH" ? "rgba(244,63,94,0.06)" : "rgba(245,158,11,0.06)"};border:1px solid ${w.severity === "HIGH" ? CN.rose + "40" : CN.amber + "40"}">
                <div style="font-size:10px;font-weight:800;color:${w.severity === "HIGH" ? CN.rose : CN.amber};margin-bottom:4px">${w.severity} SEVERITY</div>
                <div style="font-size:12px;color:${CN.textPrimary};margin-bottom:4px;font-weight:600">${w.weakness}</div>
                <div style="font-size:11px;color:${CN.textMuted}">Fix: ${w.fix}</div>
            </div>`).join("");
    }

    const opts = profile.INTERVIEW_OPTIMIZER || [];
    const op = document.getElementById("interviewOptimizerPanel");
    if (op) {
        op.innerHTML = opts.map(o => `
            <div style="display:flex;align-items:center;gap:10px;padding:8px 0;border-bottom:1px solid ${CN.borderSub}">
                <div style="height:6px;width:6px;border-radius:50%;background:${o.blocker ? CN.rose : CN.emerald};flex-shrink:0"></div>
                <div style="flex:1;min-width:0">
                    <div style="font-size:12px;font-weight:600;color:${CN.textPrimary}">${o.action}</div>
                    <div style="font-size:10px;color:${CN.textMuted}">${o.timeframe} · Effort: ${o.effort}</div>
                </div>
                <div style="font-size:13px;font-weight:800;color:${o.impact >= 90 ? CN.emerald : CN.cyan};min-width:36px;text-align:right">${o.impact}%</div>
            </div>`).join("");
    }
}

// ── Certs Pane (lazy) ──────────────────────────────────────────────────────
function renderCertsPane() {
    const profile = getActiveDashProfile();
    if (!profile) return;
    const gaps = profile.GAP_DATA || [];
    const el = document.getElementById("certGapPlanPanel");
    if (!el) return;
    el.innerHTML = gaps.map((g, i) => `
        <div style="display:flex;gap:16px;align-items:flex-start;padding:14px 0;border-bottom:1px solid ${CN.borderSub}">
            <div style="width:32px;height:32px;border-radius:8px;background:${i === 0 ? CN.rose + "18" : CN.amber + "18"};display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:800;color:${i === 0 ? CN.rose : CN.amber};flex-shrink:0">${i+1}</div>
            <div>
                <div style="font-size:12px;font-weight:600;color:${CN.textPrimary};margin-bottom:4px">${g.gap}</div>
                <div style="font-size:11px;color:${CN.textMuted};margin-bottom:6px">${g.action}</div>
                <div style="display:flex;gap:8px;flex-wrap:wrap">
                    <span style="padding:2px 8px;border-radius:10px;font-size:9px;font-weight:700;background:rgba(99,102,241,0.12);color:${CN.indigo}">ROI ${g.roi}/10</span>
                    <span style="padding:2px 8px;border-radius:10px;font-size:9px;font-weight:700;background:${CN.amber}12;color:${CN.amber}">${g.timeToImpact}d to impact</span>
                    <span style="padding:2px 8px;border-radius:10px;font-size:9px;font-weight:700;background:${CN.emerald}12;color:${CN.emerald}">${g.category.toUpperCase()}</span>
                </div>
            </div>
        </div>`).join("");
}

// ── Roadmap Pane (lazy) ────────────────────────────────────────────────────
function renderRoadmapPane() {
    const profile = getActiveDashProfile();
    if (!profile) return;

    const tl = document.getElementById("execTimelinePanel");
    if (tl) {
        const items = profile.EXEC_TIMELINE || [];
        tl.innerHTML = `<div style="display:flex;gap:12px;flex-wrap:wrap">` +
            items.map(t => `
                <div style="${glassStyle}padding:16px 18px;min-width:200px;flex:1;border-left:3px solid ${t.color}">
                    <div style="font-size:11px;font-weight:700;color:${t.color};margin-bottom:4px;text-transform:uppercase">${t.phase}</div>
                    <div style="font-size:13px;font-weight:700;color:${CN.textPrimary};margin-bottom:10px">${t.label}</div>
                    ${t.tasks.map(task => `<div style="font-size:11px;color:${CN.textSec};padding:4px 0;border-bottom:1px solid ${CN.borderSub}">▸ ${task}</div>`).join("")}
                </div>`).join("") +
            "</div>";
    }

    const arch = document.getElementById("jobEngineArchPanel");
    if (arch) {
        const layers = profile.JOB_ENGINE_DATA?.archLayers || [];
        arch.innerHTML = layers.map(l => `
            <div style="display:flex;gap:12px;align-items:center;padding:10px 0;border-bottom:1px solid ${CN.borderSub}">
                <div style="width:36px;height:36px;border-radius:8px;background:${l.color}22;display:flex;align-items:center;justify-content:center;font-size:18px;flex-shrink:0">${l.icon}</div>
                <div>
                    <div style="font-size:12px;font-weight:700;color:${l.color}">${l.layer}</div>
                    <div style="font-size:11px;color:${CN.textSec}">${l.desc}</div>
                    <div style="font-size:10px;font-family:monospace;color:${CN.textMuted}">${l.tech}</div>
                </div>
            </div>`).join("");
    }

    const sf = document.getElementById("scoringFactorsPanel");
    if (sf) {
        const factors = profile.JOB_ENGINE_DATA?.scoringFactors || [];
        sf.innerHTML = factors.map(f => `
            <div style="padding:10px 0;border-bottom:1px solid ${CN.borderSub}">
                <div style="display:flex;justify-content:space-between;margin-bottom:4px">
                    <span style="font-size:12px;font-weight:700;color:${CN.textPrimary}">${f.factor}</span>
                    <span style="font-size:11px;font-weight:800;color:${CN.indigo}">${f.weight}%</span>
                </div>
                <div style="height:4px;background:rgba(255,255,255,0.06);border-radius:2px;overflow:hidden;margin-bottom:4px">
                    <div style="height:100%;width:${f.weight * 2}%;background:linear-gradient(90deg,${CN.indigo},${CN.cyan});border-radius:2px"></div>
                </div>
                <div style="font-size:10px;color:${CN.textMuted}">${f.logic}</div>
            </div>`).join("");
    }
}

// ── Wire into profile switch ───────────────────────────────────────────────
(function wireCareerDashboard() {
    const orig = typeof switchProfile === "function" ? switchProfile : null;
    window.switchProfile = function(profileId) {
        if (orig) orig(profileId);
        _intelRendered = false;
        setTimeout(renderCareerDashboard, 80);
    };

    // Initial render
    document.addEventListener("DOMContentLoaded", function() {
        setTimeout(renderCareerDashboard, 200);
    });
})();
</script>
'''

# Remove previously injected copy (if any) to avoid duplication
new_html = re.sub(r'<script>\s*// ═+\s*// Career Navigator Dashboard.*?</script>', '', new_html, flags=re.DOTALL)

# Inject before </body>
new_html = new_html.replace('</body>', RENDER_JS + '\n</body>')

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(new_html)

print("Done. index.html successfully rebuilt.")
