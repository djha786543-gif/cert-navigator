import re
import os

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Strip the statically defined GAP_DATA, RESUME_DATA, EXEC_TIMELINE, INTERVIEW_OPTIMIZER, JOB_ENGINE_DATA block
html = re.sub(r'const RESUME_DATA = \{.*?\n\};', '', html, flags=re.DOTALL)
html = re.sub(r'const GAP_DATA = \[.*?\n\];', '', html, flags=re.DOTALL)
html = re.sub(r'const EXEC_TIMELINE = \[.*?\n\];', '', html, flags=re.DOTALL)
html = re.sub(r'const INTERVIEW_OPTIMIZER = \[.*?\n\];', '', html, flags=re.DOTALL)
html = re.sub(r'const JOB_ENGINE_DATA = \{.*?\n\};', '', html, flags=re.DOTALL)

# 2. Replace hardcoded references in rendering functions
html = html.replace('RESUME_DATA.hardSkills', 'USER_PROFILES[currentProfile].RESUME_DATA.hardSkills')
html = html.replace('RESUME_DATA.softSkills', 'USER_PROFILES[currentProfile].RESUME_DATA.softSkills')
html = html.replace('RESUME_DATA.positioningWeaknesses', 'USER_PROFILES[currentProfile].RESUME_DATA.positioningWeaknesses')

html = html.replace("const filtered = cat === 'all' ? GAP_DATA : GAP_DATA.filter", "const gapData = USER_PROFILES[currentProfile].GAP_DATA;\n    const filtered = cat === 'all' ? gapData : gapData.filter")

html = html.replace('EXEC_TIMELINE.map', 'USER_PROFILES[currentProfile].EXEC_TIMELINE.map')
html = html.replace('[...INTERVIEW_OPTIMIZER]', '[...USER_PROFILES[currentProfile].INTERVIEW_OPTIMIZER]')
html = html.replace('JOB_ENGINE_DATA.apis', 'USER_PROFILES[currentProfile].JOB_ENGINE_DATA.apis')
html = html.replace('JOB_ENGINE_DATA.scoringFactors', 'USER_PROFILES[currentProfile].JOB_ENGINE_DATA.scoringFactors')
html = html.replace('JOB_ENGINE_DATA.archLayers', 'USER_PROFILES[currentProfile].JOB_ENGINE_DATA.archLayers')
html = html.replace('JOB_ENGINE_DATA.automationSteps', 'USER_PROFILES[currentProfile].JOB_ENGINE_DATA.automationSteps')
html = html.replace('JOB_ENGINE_DATA.techStack', 'USER_PROFILES[currentProfile].JOB_ENGINE_DATA.techStack')
html = html.replace('JOB_ENGINE_DATA.optimizationEngine', 'USER_PROFILES[currentProfile].JOB_ENGINE_DATA.optimizationEngine')
html = html.replace('JOB_ENGINE_DATA.codeBlueprint', 'USER_PROFILES[currentProfile].JOB_ENGINE_DATA.codeBlueprint')
html = html.replace('JOB_ENGINE_DATA.deployOptions', 'USER_PROFILES[currentProfile].JOB_ENGINE_DATA.deployOptions')

# 3. Modify `switchProfile` to invoke new dynamic reload
old_switch = r"""function switchProfile(profileId) \{
    if\(!PROFILES\[profileId\]\) return;
    currentProfile = profileId;.*?if \(document.getElementById\('view-jobEngine'\).classList.contains\('active'\)\) \{
        renderJobEngine\(\);
    \}
\}"""

new_switch = """function switchProfile(profileId) {
    if(!USER_PROFILES[profileId]) return;
    currentProfile = profileId;
    
    const toastContainer = document.createElement('div');
    toastContainer.className = 'toast-container';
    toastContainer.innerHTML = `<div class="toast info" style="background:#1a1b2e; border:1px solid #6366f1; color:white; padding: 10px; border-radius: 8px;">Switched to ${USER_PROFILES[profileId].name}'s Profile</div>`;
    document.body.appendChild(toastContainer);
    setTimeout(() => toastContainer.remove(), 3000);

    // Swap ALL views simultaneously if they are actively showing
    if (document.getElementById('view-careerIntel').classList.contains('active')) renderCareerIntel();
    if (document.getElementById('view-jobEngine').classList.contains('active')) renderJobEngine();
    
    // Refresh global dashboard text if any
    const titleObj = document.querySelector("#view-jobEngine .view-subtitle strong");
    if(titleObj) titleObj.innerText = `${USER_PROFILES[profileId].name} (${USER_PROFILES[profileId].title})`;
}"""

html = re.sub(old_switch, new_switch, html, flags=re.DOTALL)

# 4. We should inject <script src="js/profiles.js"></script> and remove the old `const PROFILES = ...` block
html = re.sub(r'const PROFILES = \{.*?\n\};', '', html, flags=re.DOTALL)

# Check if script tag is there
if 'js/profiles.js' not in html:
    html = html.replace('</body>', '<script src="js/profiles.js"></script>\n</body>')

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)

