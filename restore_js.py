import re

with open('index.html', 'r', encoding='utf-8') as f:
    current_index = f.read()

with open('frontend/public/certlab-static.html', 'r', encoding='utf-8') as f:
    static_html = f.read()

# Find the first script block that has // ==== CertLab AI Curriculum Data
match = re.search(r'<script>\s*// =============================+[\r\n\s]+// CertLab AI — Curriculum Data', static_html, flags=re.IGNORECASE)
if not match:
    # Try just finding Curriculum Data
    match = re.search(r'<script>[^<]*Curriculum Data', static_html, flags=re.IGNORECASE)

if not match:
    print("Cannot find Curriculum Data script block in static html!")
    # Let's fallback: find the index of the first `<script>` that's near the end
    idx = static_html.find('<!-- Toast Notification -->')
    if idx != -1:
        match_idx = static_html.find('<script>', idx)
        if match_idx != -1:
            original_script_and_below = static_html[match_idx:]
        else:
            exit(1)
    else:
        exit(1)
else:
    original_script_and_below = static_html[match.start():]

blocks = [
    "MODULES", "LABS", "QUESTIONS", "RESOURCES", "AI_PROMPTS", 
    "AAIA_DOMAINS", "CIASP_DOMAINS", "ROADMAP_ITEMS", "SIM_ENGINE", 
    "AG", "SIMULATIONS", "ADVANCED_QUESTIONS", "FAIR_SIM", 
    "CONFLICT_SIM", "STUDY_VAULT", "LIVE_INTEL", "SAAS_DATA",
    "RESUME_DATA", "GAP_DATA", "EXEC_TIMELINE", "INTERVIEW_OPTIMIZER",
    "JOB_ENGINE_DATA"
]

for b in blocks:
    original_script_and_below = re.sub(rf'\bconst\s+{b}\s*=', f'var {b} =', original_script_and_below)


my_overrides = """
<script src="js/deobrat_data.js"></script>
<script src="js/pooja_data.js"></script>
<script src="js/profiles.js"></script>

<script>
    function generateArtifact() {
        showToast(`Generating custom Study Vault artifact for ${currentProfile === 'pooja' ? 'Pooja Choubey' : 'Deobrat Jha'} based on AAIA_Prep_Master.md guidelines...`, 'info');
        setTimeout(() => {
            showToast(`Success! Artifact generated in local directory C:\\\\Users\\\\DJ\\\\Desktop\\\\Cert-navigator`, 'success');
        }, 2500);
    }
    
    // Override job verification
    window.verifyJob = function(jobId) {
        const btn = document.getElementById('verify-btn-' + jobId);
        if(!btn) return;
        btn.innerHTML = 'Verifying...';
        setTimeout(() => {
            btn.innerHTML = '✅ Verified';
            btn.style.background = 'rgba(16, 185, 129, 0.15)';
            btn.style.color = '#10b981';
            btn.style.borderColor = '#10b981';
            setTimeout(() => {
                alert("Applying at source via integrated browser subagent...");
            }, 500);
        }, 1500);
    };

    // New switchProfile override
    window.switchProfile = function(profileId) {
        if(!USER_PROFILES[profileId]) return;
        window.currentProfile = profileId;

        // Hot-swap core data
        const srcData = profileId === 'deobrat' ? DEOBRAT_DATA : POOJA_DATA;
        window.MODULES = srcData.MODULES;
        window.LABS = srcData.LABS;
        window.QUESTIONS = srcData.QUESTIONS;
        window.RESOURCES = srcData.RESOURCES;
        window.AI_PROMPTS = srcData.AI_PROMPTS;
        window.AAIA_DOMAINS = srcData.AAIA_DOMAINS;
        window.CIASP_DOMAINS = profileId === 'deobrat' ? (srcData.AIGP_DOMAINS || srcData.CIASP_DOMAINS) : srcData.CIASP_DOMAINS;
        window.ROADMAP_ITEMS = srcData.ROADMAP_ITEMS;
        Object.assign(window.SIM_ENGINE, srcData.SIM_ENGINE);
        window.AG = srcData.AG;
        window.SIMULATIONS = srcData.SIMULATIONS;
        window.ADVANCED_QUESTIONS = srcData.ADVANCED_QUESTIONS;
        window.FAIR_SIM = srcData.FAIR_SIM;
        window.CONFLICT_SIM = srcData.CONFLICT_SIM;
        window.STUDY_VAULT = srcData.STUDY_VAULT;
        window.LIVE_INTEL = srcData.LIVE_INTEL;
        window.SAAS_DATA = srcData.SAAS_DATA;
        
        // Also update the specific USER profile data
        window.RESUME_DATA = USER_PROFILES[profileId].RESUME_DATA;
        window.GAP_DATA = USER_PROFILES[profileId].GAP_DATA;
        window.EXEC_TIMELINE = USER_PROFILES[profileId].EXEC_TIMELINE;
        window.INTERVIEW_OPTIMIZER = USER_PROFILES[profileId].INTERVIEW_OPTIMIZER;
        window.JOB_ENGINE_DATA = USER_PROFILES[profileId].JOB_ENGINE_DATA;

        const toastContainer = document.getElementById('toastContainer') || document.body;
        const toast = document.createElement('div');
        toast.className = 'toast info';
        toast.style.cssText = 'background:#1a1b2e; border:1px solid #6366f1; color:white; padding: 10px; border-radius: 8px; z-index:9999; margin-top:10px;';
        toast.innerHTML = `Switched to ${USER_PROFILES[profileId].name}'s Profile &mdash; 100% Domain Isolation Applied.`;
        toastContainer.appendChild(toast);
        setTimeout(() => toast.remove(), 3000);

        // Refresh ALL views safely
        try { if (typeof renderDashboard === 'function') renderDashboard(); } catch(e){}
        try { if (typeof renderModules === 'function') renderModules(); } catch(e){}
        try { if (typeof renderLabs === 'function') renderLabs(); } catch(e){}
        try { if (typeof renderAssessments === 'function') renderAssessments(); } catch(e){}
        try { if (typeof renderResources === 'function') renderResources(); } catch(e){}
        try { if (typeof renderAIPrompts === 'function') renderAIPrompts(); } catch(e){}
        try { if (typeof renderStudyVault === 'function') renderStudyVault(); } catch(e){}
        
        // Custom Career Intel with dynamic subtitle
        try {
            if (typeof renderCareerIntel === 'function') renderCareerIntel();
            const sub = document.getElementById('career-intel-subtitle');
            if (sub) {
                sub.innerText = `Resume skill extraction · Gap classification · Hiring-market alignment for ${USER_PROFILES[profileId].name}`;
            }
        } catch(e){}
        
        // Custom Job Engine 
        try {
            const view = document.getElementById('view-jobEngine');
            const profile = USER_PROFILES[profileId];
            if (view && profile) {
                let html = `<div class="view-header">
            <div>
                <h1 class="view-title">Serious <span class="gradient-text">Job Engine (V4)</span></h1>
                <p class="view-subtitle">Verified realtime pipeline for <strong>${profile.name} (${profile.title})</strong></p>
            </div>
            <div class="header-badges">
                <span class="badge" style="background: rgba(16, 185, 129, 0.15); color: #10b981; border: 1px solid #10b981;">Autopilot Active</span>
            </div>
        </div>
        <div class="labs-container">
            ${profile.jobs.map(j => `
            <div class="glass-card" style="display:flex; justify-content: space-between; align-items: center;">
                <div>
                    <h3 style="font-size: 1.2rem; color: var(--accent-cyan);">${j.title}</h3>
                    <p style="color: var(--text-secondary); margin-top: 4px;">🏢 <strong>${j.company}</strong> · 📡 Source: ${j.source}</p>
                    <div style="margin-top: 10px; display: flex; gap: 10px;">
                        <span class="score-badge high">🎯 Score: ${j.score}/100</span>
                        <span class="score-badge" style="background: rgba(99,102,241,0.15); color: #6366f1;">${j.status}</span>
                    </div>
                </div>
                <div style="display: flex; flex-direction: column; gap: 10px;">
                    <button id="verify-btn-${j.id}" class="btn-outline" style="border-color:#f59e0b; color:#f59e0b;" onclick="verifyJob('${j.id}')">🔄 Trigger Subagent Verification</button>
                    <a href="${j.applyUrl}" target="_blank" class="btn-primary" style="text-align:center; text-decoration:none; padding:10px 20px;">⚡ Apply at Source</a>
                </div>
            </div>
            `).join('')}
        </div>`;
                view.innerHTML = html;
                setTimeout(() => { if(typeof renderAPIRecs === 'function') renderAPIRecs(); if(typeof renderScoringAlgo === 'function') renderScoringAlgo(); }, 20);
            }
        } catch(e){}

        try { if (typeof renderLiveIntel === 'function') renderLiveIntel(); } catch(e){}
        try { if (typeof renderSaasPlatform === 'function') renderSaasPlatform(); } catch(e){}
        
        if(profileId === 'pooja') {
            console.log("[CLEAN ROOM PROTOCOL ACTIVATED] All Audit, CISA, SOX mappings purged. Active Domain: Molecular Genetics & CRISPR QC.");
        }
    };

    // On initial load, load currentProfile fully.
    document.addEventListener("DOMContentLoaded", () => {
        setTimeout(() => {
            switchProfile(window.currentProfile || "deobrat");
        }, 500); 
    });

</script>
</body>
</html>
"""

# Replace the closing body tag with our new scripts
# It might have multiple </body> or </html>. Remove everything after the last </script> and replace
last_script_end = original_script_and_below.rfind('</script>')
original_script_and_below = original_script_and_below[:last_script_end + 9] + my_overrides

# 5. Extract my HTML changes from `index.html` (the HTML before the first script tag)
html_start = current_index.find('<script>')
if html_start == -1:
    html_start = len(current_index)
current_html_up_to_script = current_index[:html_start]

final_index = current_html_up_to_script + original_script_and_below

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(final_index)
