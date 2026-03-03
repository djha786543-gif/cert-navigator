import re

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Strip the old CSS nav definition and .main-content rules.
html = re.sub(r'/\* === Navigation === \*/.*?/\* === Main Content === \*/\s*\.main-content\s*{[^}]+}', '''
        /* === Navigation Redefined to Top Header === */
        header.top-header {
            background: var(--bg-glass);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border-bottom: 1px solid var(--border-subtle);
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 12px 28px;
            position: sticky;
            top: 0;
            z-index: 100;
        }

        .header-left { display: flex; align-items: center; gap: 16px; }
        .header-logo {
            width: 36px; height: 36px; border-radius: 10px;
            background: var(--gradient-primary); display: flex;
            align-items: center; justify-content: center; font-size: 18px; font-weight: 800; color: #fff;
        }
        .header-title { font-weight: 700; font-size: 16px; color: var(--text-primary); }
        .header-subtitle { font-size: 11px; color: var(--text-muted); }

        .header-right { display: flex; align-items: center; gap: 12px; }
        .user-toggle {
            display: flex; gap: 4px; background: var(--bg-tertiary);
            border-radius: 10px; padding: 4px; border: 1px solid var(--border-subtle);
        }
        .user-btn {
            padding: 5px 14px; border-radius: 7px; border: none; cursor: pointer;
            font-size: 12px; font-weight: 700; transition: all 0.2s; background: transparent; color: var(--text-secondary);
        }
        .user-btn.active { background: var(--gradient-primary); color: #fff; }

        .nav-tabs {
            display: flex; gap: 4px; overflow-x: auto; padding: 20px 28px 0;
            border-bottom: 1px solid var(--border-subtle); align-items: flex-end;
        }
        .nav-link {
            padding: 8px 18px; border: none; cursor: pointer; font-size: 13px; font-weight: 600;
            border-radius: 8px 8px 0 0; transition: all 0.2s; background: transparent; color: var(--text-secondary);
            border-bottom: 2px solid transparent; text-decoration: none; white-space: nowrap; margin-bottom: -1px;
        }
        .nav-link:hover { background: var(--bg-glass); color: var(--text-primary); }
        .nav-link.active {
            background: var(--bg-glass); color: var(--text-primary);
            border-bottom: 2px solid var(--accent-indigo);
        }

        .main-content {
            padding: 24px 28px 48px;
            position: relative;
            z-index: 1;
            min-height: 100vh;
        }
''', html, flags=re.DOTALL)

# Delete the ENTIRE <nav ...> node
html = re.sub(r'<nav class="main-nav"[^>]*>.*?</nav>\s*', '', html, flags=re.DOTALL)

# Insert the top-header
new_header = """
    <header class="top-header">
        <div class="header-left">
            <div class="header-logo">C</div>
            <div>
                <div class="header-title">Career Navigator</div>
                <div class="header-subtitle">Resilience-Linked Career Engine</div>
            </div>
        </div>
        <div class="header-right">
            <div class="user-toggle">
                <button class="user-btn active" id="btn-deobrat" onclick="topSwitchProfile('deobrat')">Deobrat Jha</button>
                <button class="user-btn" id="btn-pooja" onclick="topSwitchProfile('pooja')">Pooja Choubey</button>
            </div>
            <a href="#" style="padding:6px 14px; border-radius:8px; border:1px solid rgba(99,102,241,0.25); color:var(--text-secondary); text-decoration:none; font-size:13px;">Profile</a>
        </div>
    </header>

    <div class="nav-tabs">
        <button class="nav-link active" onclick="switchViewExtended('dashboard'); setActiveTab(this)">Dashboard</button>
        <button class="nav-link" onclick="switchViewExtended('jobEngine'); setActiveTab(this)">Serious Job Engine</button>
        <button class="nav-link" onclick="switchViewExtended('labs'); setActiveTab(this)">Real-World Labs</button>
        <button class="nav-link" onclick="switchViewExtended('studyVault'); setActiveTab(this)">Study Vault</button>
        <button class="nav-link" onclick="switchViewExtended('careerIntel'); setActiveTab(this)">Career Intel</button>
        <button class="nav-link" onclick="switchViewExtended('saasPlatform'); setActiveTab(this)">SaaS Platform</button>
        <button class="nav-link" onclick="switchViewExtended('liveIntel'); setActiveTab(this)">Market Intel</button>
    </div>
"""

# Replace all the duplicate headers we accidentally injected just now if any
html = re.sub(r'<header class="top-header">.*?</header>\s*<div class="nav-tabs">.*?</div>\s*', '', html, flags=re.DOTALL)

html = html.replace('<main class="main-content">', new_header + '\n    <main class="main-content">')

js_additions = """
    function setActiveTab(el) {
        document.querySelectorAll('.nav-link').forEach(btn => btn.classList.remove('active'));
        if(el) el.classList.add('active');
    }
    window.topSwitchProfile = function(id) {
        document.getElementById('btn-deobrat').classList.remove('active');
        document.getElementById('btn-pooja').classList.remove('active');
        document.getElementById('btn-' + id).classList.add('active');
        if(typeof switchProfile === 'function') switchProfile(id);
    };
"""

# We'll just tack the js_additions before </body>
html = html.replace('</body>', js_additions + '\n</body>')

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)
