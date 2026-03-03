import re
import json

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# All data blocks to extract
blocks = [
    "MODULES", "LABS", "QUESTIONS", "RESOURCES", "AI_PROMPTS", 
    "AAIA_DOMAINS", "CIASP_DOMAINS", "ROADMAP_ITEMS", "SIM_ENGINE", 
    "AG", "SIMULATIONS", "ADVANCED_QUESTIONS", "FAIR_SIM", 
    "CONFLICT_SIM", "STUDY_VAULT", "LIVE_INTEL", "SAAS_DATA"
]

deobrat_js = "const DEOBRAT_DATA = {\n"

for block in blocks:
    pattern = rf"const {block} = (\[.*?\]|\{{.*?\}});\s*(?=(?:const [A-Z_]+ =|let state =|function))"
    match = re.search(pattern, html, flags=re.DOTALL)
    if match:
        data_str = match.group(1)
        deobrat_js += f"  {block}: {data_str},\n"
        # Optional: remove from HTML
        # We will do this later to avoid breaking the file before testing
        
deobrat_js += "};\n"

with open('js/deobrat_data.js', 'w', encoding='utf-8') as f:
    f.write(deobrat_js)
