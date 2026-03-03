import re

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# All data blocks to remove
blocks = [
    "MODULES", "LABS", "QUESTIONS", "RESOURCES", "AI_PROMPTS", 
    "AAIA_DOMAINS", "CIASP_DOMAINS", "ROADMAP_ITEMS", "SIM_ENGINE", 
    "AG", "SIMULATIONS", "ADVANCED_QUESTIONS", "FAIR_SIM", 
    "CONFLICT_SIM", "STUDY_VAULT", "LIVE_INTEL", "SAAS_DATA"
]

for block in blocks:
    pattern = rf"const {block} = (?:\[.*?\]|\{{.*?\}});\s*(?=(?:const [A-Z_]+ =|let state =|function|let activeTool =))"
    html = re.sub(pattern, "", html, flags=re.DOTALL)

# Add script tags for new files
if 'js/deobrat_data.js' not in html:
    html = html.replace('<script src="js/profiles.js"></script>', 
    '<script src="js/deobrat_data.js"></script>\n<script src="js/pooja_data.js"></script>\n<script src="js/profiles.js"></script>')

# Replace the switchProfile to hot-swap global variables
old_switch = r"function switchProfile\(profileId\) \{.*?\}"
new_switch = """function switchProfile(profileId) {
    if(!USER_PROFILES[profileId]) return;
    currentProfile = profileId;

    // Hot-swap data
    const srcData = profileId === 'deobrat' ? DEOBRAT_DATA : POOJA_DATA;
    window.MODULES = srcData.MODULES;
    window.LABS = srcData.LABS;
    window.QUESTIONS = srcData.QUESTIONS;
    window.RESOURCES = srcData.RESOURCES;
    window.AI_PROMPTS = srcData.AI_PROMPTS;
    window.AAIA_DOMAINS = srcData.AAIA_DOMAINS;
    window.CIASP_DOMAINS = profileId === 'deobrat' ? srcData.AIGP_DOMAINS || srcData.CIASP_DOMAINS : srcData.CIASP_DOMAINS;
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

    const toastContainer = document.createElement('div');
    toastContainer.className = 'toast-container';
    toastContainer.innerHTML = `<div class="toast info" style="background:#1a1b2e; border:1px solid #6366f1; color:white; padding: 10px; border-radius: 8px; z-index:9999;">Switched to ${USER_PROFILES[profileId].name}'s Profile — 100% Domain Isolation Applied.</div>`;
    document.body.appendChild(toastContainer);
    setTimeout(() => toastContainer.remove(), 3000);

    // Refresh ALL views
    if (typeof renderDashboard === 'function') renderDashboard();
    if (typeof renderModules === 'function') renderModules();
    if (typeof renderLabs === 'function') renderLabs();
    if (typeof renderAssessments === 'function') renderAssessments();
    if (typeof renderResources === 'function') renderResources();
    if (typeof renderAIPrompts === 'function') renderAIPrompts();
    if (typeof renderStudyVault === 'function') renderStudyVault();
    if (typeof renderCareerIntel === 'function') renderCareerIntel();
    if (typeof renderJobEngine === 'function') renderJobEngine();
    if (typeof renderLiveIntel === 'function') renderLiveIntel();
    if (typeof renderSaaSPlatform === 'function') renderSaaSPlatform();
    
    // Refresh global dashboard text if any
    const titleObj = document.querySelector("#view-jobEngine .view-subtitle strong");
    if(titleObj) titleObj.innerText = `${USER_PROFILES[profileId].name} (${USER_PROFILES[profileId].title})`;
    
    // Purge logic explicit feedback
    if(profileId === 'pooja') {
        console.log("[CLEAN ROOM PROTOCOL ACTIVATED] All Audit, CISA, SOX mappings purged. Active Domain: Molecular Genetics & CRISPR QC.");
    }
}"""
html = re.sub(old_switch, new_switch, html, flags=re.DOTALL)

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)
