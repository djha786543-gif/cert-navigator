"""Inject Career Center view and script tags into index.html."""
import re

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# ─── 1. Inject Career Center nav tab into the top nav bar ─────────────────
# Find the nav-tabs section and add Career Center if not there
if 'switchViewExtended(\'careerCenter\')' not in html:
    # Find the last nav-link button and insert after it
    html = html.replace(
        "onclick=\"switchViewExtended('careerIntel'); setActiveTab(this)\">Career Intel</button>",
        "onclick=\"switchViewExtended('careerIntel'); setActiveTab(this)\">Career Intel</button>\n        <button class=\"nav-link\" onclick=\"switchViewExtended('careerCenter'); setActiveTab(this)\">Career Center</button>"
    )
    print("Nav tab injected.")
else:
    print("Nav tab already present.")

# ─── 2. Inject Career Center view section before </main> ──────────────────
CAREER_CENTER_VIEW = '''
        <!-- ============ CAREER CENTER VIEW ============ -->
        <section class="view" id="view-careerCenter">
            <div class="view-header" style="margin-bottom:20px">
                <div>
                    <h1 class="view-title">Career <span class="gradient-text">Center</span></h1>
                    <p class="view-subtitle" id="ccSubtitle">Your complete standalone career navigation system — certifications, market intel, interview prep, resume, networking & action plan.</p>
                </div>
            </div>
            <div id="careerCenterRoot">
                <div style="text-align:center;padding:60px 20px;color:#5f6580;font-size:14px">Loading career data...</div>
            </div>
        </section>
'''

if 'id="view-careerCenter"' not in html:
    # Insert before closing </main>
    html = html.replace('</main>', CAREER_CENTER_VIEW + '\n    </main>')
    print("Career Center view section injected.")
else:
    print("Career Center view already present.")

# ─── 3. Inject script tags before </body> ─────────────────────────────────
SCRIPTS = '''
    <!-- Career Navigator Standalone System -->
    <script src="js/career_data.js"></script>
    <script src="js/career_engine.js"></script>
'''

if 'career_data.js' not in html:
    html = html.replace('</body>', SCRIPTS + '\n</body>')
    print("Script tags injected.")
else:
    print("Scripts already present.")

# ─── 4. Wire careerCenter into switchViewExtended ─────────────────────────
if "viewName === 'careerCenter'" not in html:
    # Find switchViewExtended function and add careerCenter rendering
    html = html.replace(
        "if (viewName === 'careerIntel') setTimeout(renderCareerIntel, 60);",
        "if (viewName === 'careerIntel') setTimeout(renderCareerIntel, 60);\n                if (viewName === 'careerCenter') setTimeout(()=>{ if(typeof renderCareerCenter==='function') renderCareerCenter(); }, 80);"
    )
    print("switchViewExtended hook injected.")
else:
    print("switchViewExtended hook already present.")

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("\nDone. index.html updated with Career Center.")
