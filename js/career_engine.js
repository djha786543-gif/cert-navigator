// ═══════════════════════════════════════════════════════════════════════════
// CAREER NAVIGATOR — Standalone Career Center Render Engine
// Reads CAREER_INTELLIGENCE[profile] and renders all sections
// ═══════════════════════════════════════════════════════════════════════════

(function () {
    'use strict';

    // ── Utility ─────────────────────────────────────────────────────────────────
    const $ = id => document.getElementById(id);
    const esc = s => String(s).replace(/</g, '&lt;').replace(/>/g, '&gt;');
    const C = {
        indigo: "#6366f1", cyan: "#06b6d4", purple: "#a855f7", amber: "#f59e0b",
        emerald: "#10b981", rose: "#f43f5e", textP: "#e8e9f3", textS: "#9ca3b8",
        textM: "#5f6580", bg: "rgba(18,19,31,0.75)", bgT: "#1a1b2e",
        bs: "rgba(99,102,241,0.12)", bm: "rgba(99,102,241,0.25)"
    };
    const glass = (extra = '') => `background:${C.bg};backdrop-filter:blur(12px);border:1px solid ${C.bs};border-radius:12px;${extra}`;
    const urgencyColor = { IMMEDIATE: C.rose, SHORT: C.amber, MEDIUM: C.cyan, LONG: C.purple, LONG_TERM: C.purple };

    function activeData() {
        const id = (typeof currentProfile !== 'undefined') ? currentProfile : 'deobrat';
        return (typeof CAREER_INTELLIGENCE !== 'undefined' && CAREER_INTELLIGENCE[id]) ? CAREER_INTELLIGENCE[id] : null;
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // CAREER CENTER VIEW — main render
    // ═══════════════════════════════════════════════════════════════════════════
    window.renderCareerCenter = function () {
        const d = activeData(); if (!d) return;
        const el = $('careerCenterRoot'); if (!el) return;

        el.innerHTML = `
  <!-- Hero Banner -->
  <div style="${glass('padding:20px 24px;margin-bottom:20px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px')}">
    <div>
      <div style="font-size:11px;color:${C.indigo};font-weight:700;text-transform:uppercase;letter-spacing:.08em;margin-bottom:4px">Career Intelligence Hub</div>
      <div style="font-size:22px;font-weight:800;color:${C.textP}">${d.trajectory.current.title}</div>
      <div style="font-size:13px;color:${C.textS};margin-top:4px">${d.trajectory.market_signal}</div>
    </div>
    <div style="display:flex;gap:10px;flex-wrap:wrap">
      <div style="${glass('padding:12px 16px;text-align:center;min-width:100px')}">
        <div style="font-size:18px;font-weight:800;color:${C.emerald}">${d.trajectory.target12.probability}%</div>
        <div style="font-size:10px;color:${C.textM}">12-Month Probability</div>
      </div>
      <div style="${glass('padding:12px 16px;text-align:center;min-width:100px')}">
        <div style="font-size:18px;font-weight:800;color:${C.cyan}">${d.trajectory.target12.salary}</div>
        <div style="font-size:10px;color:${C.textM}">Target Salary</div>
      </div>
      <div style="${glass('padding:12px 16px;text-align:center;min-width:100px')}">
        <div style="font-size:13px;font-weight:800;color:${d.trajectory.disruption_risk === 'LOW' ? C.emerald : C.amber}">${d.trajectory.disruption_risk}</div>
        <div style="font-size:10px;color:${C.textM}">AI Disruption Risk</div>
      </div>
    </div>
  </div>

  <!-- Inner tab strip -->
  <div style="display:flex;gap:4px;border-bottom:1px solid ${C.bs};margin-bottom:20px;overflow-x:auto">
    ${['trajectory', 'certs', 'interview', 'resume', 'linkedin', 'network', 'market', 'studyvault', 'action'].map((t, i) =>
            `<button id="cc-btn-${t}" onclick="switchCCTab('${t}')" style="padding:7px 14px;border:none;cursor:pointer;font-size:12px;font-weight:600;border-radius:8px 8px 0 0;background:${i === 0 ? C.bg : 'transparent'};color:${i === 0 ? C.textP : C.textS};border-bottom:${i === 0 ? `2px solid ${C.indigo}` : '2px solid transparent'};white-space:nowrap;transition:all .2s;margin-bottom:-1px">${t === 'studyvault' ? 'Study Vault' : t === 'action' ? 'Action Plan' : t.charAt(0).toUpperCase() + t.slice(1)}</button>`
        ).join('')}
  </div>

  <!-- Panes -->
  <div id="cc-trajectory" class="cc-pane">${renderTrajectory(d)}</div>
  <div id="cc-certs" class="cc-pane" style="display:none">${renderCertsCatalog(d)}</div>
  <div id="cc-interview" class="cc-pane" style="display:none">${renderInterview(d)}</div>
  <div id="cc-resume" class="cc-pane" style="display:none">${renderResume(d)}</div>
  <div id="cc-linkedin" class="cc-pane" style="display:none">${renderLinkedIn(d)}</div>
  <div id="cc-network" class="cc-pane" style="display:none">${renderNetwork(d)}</div>
  <div id="cc-market" class="cc-pane" style="display:none">${renderMarket(d)}</div>
  <div id="cc-studyvault" class="cc-pane" style="display:none">${renderStudyVault(d)}</div>
  <div id="cc-action" class="cc-pane" style="display:none">${renderActionPlan(d)}</div>
  `;
    };

    window.switchCCTab = function (tab) {
        document.querySelectorAll('.cc-pane').forEach(p => p.style.display = 'none');
        const pane = $('cc-' + tab); if (pane) pane.style.display = '';
        document.querySelectorAll('[id^="cc-btn-"]').forEach(b => {
            const isA = b.id === 'cc-btn-' + tab;
            b.style.background = isA ? C.bg : 'transparent';
            b.style.color = isA ? C.textP : C.textS;
            b.style.borderBottom = isA ? `2px solid ${C.indigo}` : '2px solid transparent';
        });
    };

    // ── TRAJECTORY ──────────────────────────────────────────────────────────────
    function renderTrajectory(d) {
        const t = d.trajectory;
        const steps = [
            { label: 'Now', title: t.current.title, salary: t.current.salary, pct: 100, color: C.textM, yoe: t.current.yoe },
            { label: '12 Mo', title: t.target12.title, salary: t.target12.salary, pct: t.target12.probability, color: C.cyan, yoe: '' },
            { label: '3 Yr', title: t.target36.title, salary: t.target36.salary, pct: t.target36.probability, color: C.indigo, yoe: '' },
            { label: 'North Star', title: t.north_star.title, salary: t.north_star.salary, pct: t.north_star.probability, color: C.purple, yoe: '' },
        ];
        return `
  <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:14px;margin-bottom:20px">
    ${steps.map((s, i) => `
    <div style="${glass('padding:18px 20px;position:relative;overflow:hidden')};transition:all .3s" onmouseover="this.style.borderColor='${s.color}'" onmouseout="this.style.borderColor='${C.bs}'">
      ${i < steps.length - 1 ? `<div style="position:absolute;right:-8px;top:50%;transform:translateY(-50%);font-size:18px;color:${C.bs};z-index:1">▶</div>` : ''}
      <div style="font-size:10px;font-weight:700;color:${s.color};text-transform:uppercase;letter-spacing:.06em;margin-bottom:6px">${s.label}</div>
      <div style="font-size:13px;font-weight:700;color:${C.textP};margin-bottom:8px;line-height:1.3">${s.title}</div>
      <div style="font-size:16px;font-weight:800;color:${s.color};margin-bottom:8px">${s.salary}</div>
      <div style="height:4px;background:rgba(255,255,255,0.06);border-radius:2px;overflow:hidden">
        <div style="height:100%;width:${s.pct}%;background:${s.color};border-radius:2px;transition:width 1s ease"></div>
      </div>
      <div style="font-size:10px;color:${C.textM};margin-top:4px">${s.pct === 100 ? 'Current position' : `${s.pct}% probability`}</div>
    </div>`).join('')}
  </div>
  <div style="${glass('padding:16px 20px')}">
    <div style="font-size:11px;font-weight:700;color:${C.amber};text-transform:uppercase;letter-spacing:.06em;margin-bottom:8px">📡 Market Signal</div>
    <div style="font-size:13px;color:${C.textS};line-height:1.7">${t.market_signal}</div>
  </div>`;
    }

    // ── CERTIFICATIONS CATALOG ──────────────────────────────────────────────────
    function renderCertsCatalog(d) {
        return d.certifications.map(c => `
  <div style="${glass('margin-bottom:14px;overflow:hidden')}">
    <div style="padding:14px 18px;display:flex;align-items:center;gap:14px;flex-wrap:wrap;cursor:pointer;border-bottom:1px solid ${C.bs}" onclick="toggleCC('cert-${c.id}')">
      <div style="width:44px;height:44px;border-radius:10px;background:${urgencyColor[c.urgency] || C.indigo}18;display:flex;align-items:center;justify-content:center;font-size:13px;font-weight:800;color:${urgencyColor[c.urgency] || C.indigo};flex-shrink:0">${c.id.slice(0, 4)}</div>
      <div style="flex:1;min-width:0">
        <div style="font-size:14px;font-weight:700;color:${C.textP}">${c.name}</div>
        <div style="font-size:11px;color:${C.textM}">${c.issuer} · ${c.timeline} · ${c.cost}</div>
      </div>
      <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
        <span style="padding:3px 10px;border-radius:12px;font-size:10px;font-weight:800;background:${urgencyColor[c.urgency] || C.indigo}18;color:${urgencyColor[c.urgency] || C.indigo};border:1px solid ${urgencyColor[c.urgency] || C.indigo}40">${c.status}</span>
        <span style="font-size:11px;color:${C.textM}">Pass rate: ${c.pass_rate}</span>
        <span style="font-size:16px;color:${C.textM}">▼</span>
      </div>
    </div>
    <div id="cert-${c.id}" style="display:none;padding:16px 18px">
      <div style="font-size:12px;color:${C.emerald};background:${C.emerald}10;padding:10px 14px;border-radius:8px;border-left:3px solid ${C.emerald};margin-bottom:14px"><strong>Why now:</strong> ${c.why}</div>
      <div style="font-size:12px;font-weight:700;color:${C.indigo};margin-bottom:8px">ROI: ${c.roi}</div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:14px">
        <div>
          <div style="font-size:11px;font-weight:700;color:${C.textP};margin-bottom:6px;text-transform:uppercase;letter-spacing:.04em">Exam Domains</div>
          ${c.domains.map(d => `<div style="font-size:11px;color:${C.textS};padding:3px 0;border-bottom:1px solid ${C.bs}">• ${d}</div>`).join('')}
        </div>
        <div>
          <div style="font-size:11px;font-weight:700;color:${C.textP};margin-bottom:6px;text-transform:uppercase;letter-spacing:.04em">Top Exam Questions</div>
          ${c.top_questions.map((q, i) => `<div style="font-size:11px;color:${C.textS};padding:4px 0;border-bottom:1px solid ${C.bs}"><span style="color:${C.amber};font-weight:700">Q${i + 1}:</span> ${q}</div>`).join('')}
        </div>
      </div>
      <div>
        <div style="font-size:11px;font-weight:700;color:${C.textP};margin-bottom:6px;text-transform:uppercase;letter-spacing:.04em">Study Resources</div>
        <div style="display:flex;gap:8px;flex-wrap:wrap">
          ${c.resources.map(r => `<span style="padding:4px 12px;border-radius:20px;font-size:11px;background:rgba(99,102,241,0.1);color:${C.indigo};border:1px solid ${C.bm}">${r}</span>`).join('')}
        </div>
      </div>
    </div>
  </div>`).join('');
    }

    // ── INTERVIEW PREP ──────────────────────────────────────────────────────────
    function renderInterview(d) {
        const iv = d.interview;
        return `
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px">
    <div style="${glass('padding:16px 20px')}">
      <div style="font-size:12px;font-weight:700;color:${C.textP};margin-bottom:4px">Salary Target</div>
      <div style="font-size:24px;font-weight:800;color:${C.emerald}">${iv.salary_negotiation.target_range}</div>
      <div style="font-size:11px;color:${C.textM}">Anchor at: ${iv.salary_negotiation.anchor}</div>
    </div>
    <div style="${glass('padding:16px 20px')}">
      <div style="font-size:12px;font-weight:700;color:${C.textP};margin-bottom:8px">Walk-Away Floor</div>
      <div style="font-size:24px;font-weight:800;color:${C.rose}">${iv.salary_negotiation.walk_away}</div>
      <div style="font-size:11px;color:${C.textM}">Never accept below this</div>
    </div>
  </div>

  <div style="${glass('padding:16px 20px;margin-bottom:16px')}">
    <div style="font-size:12px;font-weight:700;color:${C.amber};margin-bottom:8px">💰 Negotiation Script</div>
    <div style="font-size:12px;color:${C.textS};line-height:1.7;font-style:italic">"${iv.salary_negotiation.counter_script}"</div>
    <div style="margin-top:10px">
      <div style="font-size:11px;font-weight:700;color:${C.textM};margin-bottom:6px">Your Leverage Points:</div>
      ${iv.salary_negotiation.justification.map(j => `<div style="font-size:11px;color:${C.textS};padding:3px 0">✓ ${j}</div>`).join('')}
    </div>
  </div>

  <div style="font-size:13px;font-weight:700;color:${C.textP};margin-bottom:12px">Behavioral Questions — STAR Method</div>
  ${iv.behavioral.map((q, i) => `
  <div style="${glass('margin-bottom:12px;overflow:hidden')}">
    <div style="padding:12px 16px;cursor:pointer;background:rgba(99,102,241,0.05)" onclick="toggleCC('bq-${i}')">
      <div style="font-size:12px;font-weight:700;color:${C.indigo}">Q${i + 1}: ${q.q}</div>
    </div>
    <div id="bq-${i}" style="display:none;padding:14px 16px">
      ${['S', 'T', 'A', 'R'].map(k => `
      <div style="display:flex;gap:10px;margin-bottom:10px">
        <div style="width:24px;height:24px;border-radius:6px;background:${C.indigo}22;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:800;color:${C.indigo};flex-shrink:0">${k}</div>
        <div style="font-size:12px;color:${C.textS};line-height:1.6">${q.star[k === 'S' ? 'S' : k === 'T' ? 'T' : k === 'A' ? 'A' : 'R']}</div>
      </div>`).join('')}
      <div style="padding:8px 12px;background:${C.amber}10;border-left:2px solid ${C.amber};border-radius:0 6px 6px 0;font-size:11px;color:${C.amber};margin-top:8px">💡 ${q.tip}</div>
    </div>
  </div>`).join('')}

  <div style="font-size:13px;font-weight:700;color:${C.textP};margin:20px 0 12px">Technical Questions & Answers</div>
  ${iv.technical.map((q, i) => `
  <div style="${glass('margin-bottom:12px;overflow:hidden')}">
    <div style="padding:12px 16px;cursor:pointer;background:rgba(6,182,212,0.05)" onclick="toggleCC('tq-${i}')">
      <div style="font-size:12px;font-weight:700;color:${C.cyan}">T${i + 1}: ${q.q}</div>
    </div>
    <div id="tq-${i}" style="display:none;padding:14px 16px">
      <div style="font-size:12px;color:${C.textS};line-height:1.7;font-family:monospace;white-space:pre-wrap">${q.a}</div>
    </div>
  </div>`).join('')}`;
    }

    // ── RESUME ──────────────────────────────────────────────────────────────────
    function renderResume(d) {
        const r = d.resume;
        return `
  <div style="${glass('padding:16px 20px;margin-bottom:14px')}">
    <div style="font-size:11px;font-weight:700;color:${C.indigo};text-transform:uppercase;letter-spacing:.06em;margin-bottom:8px">Optimized Headline</div>
    <div style="font-size:13px;font-weight:700;color:${C.textP};padding:12px;background:${C.bgT};border-radius:8px;border-left:3px solid ${C.indigo}">${r.headline}</div>
  </div>
  <div style="${glass('padding:16px 20px;margin-bottom:14px')}">
    <div style="font-size:11px;font-weight:700;color:${C.emerald};text-transform:uppercase;letter-spacing:.06em;margin-bottom:10px">Power Bullet Points — Copy-Paste Ready</div>
    ${r.power_bullets.map((b, i) => `
    <div style="display:flex;gap:10px;align-items:flex-start;padding:8px 0;border-bottom:1px solid ${C.bs}">
      <div style="width:20px;height:20px;border-radius:5px;background:${C.emerald}18;display:flex;align-items:center;justify-content:center;font-size:10px;font-weight:800;color:${C.emerald};flex-shrink:0">${i + 1}</div>
      <div style="font-size:12px;color:${C.textS};line-height:1.6">${b}
        <span onclick="navigator.clipboard.writeText('${b.replace(/'/g, "\\'")}');this.textContent='✓ Copied!';setTimeout(()=>this.textContent='Copy',1500)"
          style="margin-left:8px;font-size:10px;color:${C.indigo};cursor:pointer;padding:2px 8px;border-radius:10px;border:1px solid ${C.bs}">Copy</span>
      </div>
    </div>`).join('')}
  </div>
  <div style="${glass('padding:16px 20px;margin-bottom:14px')}">
    <div style="font-size:11px;font-weight:700;color:${C.cyan};text-transform:uppercase;letter-spacing:.06em;margin-bottom:10px">ATS Keyword Injection List</div>
    <div style="display:flex;flex-wrap:wrap;gap:6px">
      ${r.keywords_inject.map(k => `<span style="padding:4px 12px;border-radius:20px;font-size:11px;background:rgba(6,182,212,0.1);color:${C.cyan};border:1px solid rgba(6,182,212,0.25)">${k}</span>`).join('')}
    </div>
  </div>
  <div style="${glass('padding:16px 20px')}">
    <div style="font-size:11px;font-weight:700;color:${C.amber};text-transform:uppercase;letter-spacing:.06em;margin-bottom:10px">ATS Score Optimization Tips</div>
    ${r.ats_score_tips.map(t => `<div style="font-size:12px;color:${C.textS};padding:6px 0;border-bottom:1px solid ${C.bs}">⚡ ${t}</div>`).join('')}
  </div>`;
    }

    // ── LINKEDIN ─────────────────────────────────────────────────────────────────
    function renderLinkedIn(d) {
        const l = d.linkedin;
        return `
  <div style="${glass('padding:16px 20px;margin-bottom:14px')}">
    <div style="font-size:11px;font-weight:700;color:${C.indigo};text-transform:uppercase;letter-spacing:.06em;margin-bottom:6px">Optimized Headline</div>
    <div style="font-size:13px;color:${C.textP};padding:12px;background:${C.bgT};border-radius:8px;border-left:3px solid ${C.indigo}">${l.headline}</div>
  </div>
  <div style="${glass('padding:16px 20px;margin-bottom:14px')}">
    <div style="font-size:11px;font-weight:700;color:${C.cyan};text-transform:uppercase;letter-spacing:.06em;margin-bottom:6px">About Section Hook</div>
    <div style="font-size:12px;color:${C.textS};padding:12px;background:${C.bgT};border-radius:8px;line-height:1.7;font-style:italic">"${l.about_hook}"</div>
  </div>
  <div style="${glass('padding:16px 20px;margin-bottom:14px')}">
    <div style="font-size:11px;font-weight:700;color:${C.emerald};text-transform:uppercase;letter-spacing:.06em;margin-bottom:10px">Content Pillars — Post Calendar</div>
    ${l.content_pillars.map(p => `
    <div style="display:flex;gap:12px;align-items:flex-start;padding:10px 0;border-bottom:1px solid ${C.bs}">
      <div style="flex-shrink:0;min-width:90px;font-size:10px;font-weight:700;color:${C.indigo};background:${C.indigo}12;padding:3px 8px;border-radius:10px;text-align:center">${p.frequency}</div>
      <div>
        <div style="font-size:12px;font-weight:700;color:${C.textP}">${p.topic}</div>
        <div style="font-size:11px;color:${C.textM}">Format: ${p.format}</div>
      </div>
    </div>`).join('')}
  </div>
  <div style="${glass('padding:16px 20px')}">
    <div style="font-size:11px;font-weight:700;color:${C.amber};text-transform:uppercase;letter-spacing:.06em;margin-bottom:10px">Target Connection Strategy</div>
    ${l.target_connections.map(t => `<div style="font-size:12px;color:${C.textS};padding:5px 0;border-bottom:1px solid ${C.bs}">→ ${t}</div>`).join('')}
  </div>`;
    }

    // ── NETWORK ─────────────────────────────────────────────────────────────────
    function renderNetwork(d) {
        const n = d.networking;
        return `
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:14px">
    ${n.communities.map(c => `
    <div style="${glass('padding:16px 18px')}">
      <div style="font-size:13px;font-weight:700;color:${C.textP};margin-bottom:6px">${c.name}</div>
      <div style="font-size:11px;color:${C.textS};margin-bottom:10px">${c.action}</div>
      <a href="${c.url}" target="_blank" rel="noopener" style="font-size:11px;color:${C.indigo};text-decoration:none">Visit ↗</a>
    </div>`).join('')}
  </div>
  <div style="${glass('padding:16px 20px')}">
    <div style="font-size:11px;font-weight:700;color:${C.cyan};text-transform:uppercase;letter-spacing:.06em;margin-bottom:8px">Outreach Message Template</div>
    <div style="font-size:12px;color:${C.textS};line-height:1.7;padding:12px;background:${C.bgT};border-radius:8px;font-style:italic">"${n.outreach_template}"</div>
    <button onclick="navigator.clipboard.writeText('${n.outreach_template.replace(/'/g, "\\'")}');this.textContent='✓ Copied!';setTimeout(()=>this.textContent='Copy Template',1500)"
      style="margin-top:10px;padding:7px 16px;border-radius:8px;border:1px solid ${C.bs};background:transparent;color:${C.indigo};cursor:pointer;font-size:12px;font-weight:700">Copy Template</button>
  </div>`;
    }

    // ── MARKET INTELLIGENCE ──────────────────────────────────────────────────────
    function renderMarket(d) {
        const m = d.market;
        return `
  <div style="${glass('padding:16px 20px;margin-bottom:14px')}">
    <div style="font-size:11px;font-weight:700;color:${C.amber};text-transform:uppercase;letter-spacing:.06em;margin-bottom:8px">📡 Market Narrative</div>
    <div style="font-size:13px;color:${C.textS};line-height:1.7">${m.market_narrative}</div>
  </div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:14px">
    <div style="${glass('padding:16px 20px')}">
      <div style="font-size:11px;font-weight:700;color:${C.emerald};text-transform:uppercase;letter-spacing:.06em;margin-bottom:10px">Salary Bands</div>
      ${m.salary_bands.map(s => `
      <div style="padding:10px 0;border-bottom:1px solid ${C.bs}">
        <div style="font-size:12px;font-weight:700;color:${C.textP}">${s.role}</div>
        <div style="font-size:18px;font-weight:800;color:${C.emerald}">${s.median}</div>
        <div style="font-size:10px;color:${C.textM}">Range: ${s.range} · ${s.location}</div>
      </div>`).join('')}
    </div>
    <div style="${glass('padding:16px 20px')}">
      <div style="font-size:11px;font-weight:700;color:${C.cyan};text-transform:uppercase;letter-spacing:.06em;margin-bottom:10px">🚀 Rising Skills Demand</div>
      ${m.skills_rising.map(s => `
      <div style="display:flex;align-items:center;justify-content:space-between;padding:7px 0;border-bottom:1px solid ${C.bs}">
        <div style="font-size:12px;color:${C.textS}">${s.skill}</div>
        <span style="font-size:12px;font-weight:800;color:${C.emerald}">${s.delta}</span>
      </div>`).join('')}
    </div>
  </div>
  <div style="${glass('padding:16px 20px')}">
    <div style="font-size:11px;font-weight:700;color:${C.indigo};text-transform:uppercase;letter-spacing:.06em;margin-bottom:10px">Top Hiring Organizations</div>
    <div style="display:flex;flex-wrap:wrap;gap:8px">
      ${m.top_hiring.map(c => `<span style="padding:5px 14px;border-radius:20px;font-size:12px;font-weight:600;background:rgba(99,102,241,0.08);color:${C.textS};border:1px solid ${C.bs}">${c}</span>`).join('')}
    </div>
  </div>`;
    }

    // ── STUDY VAULT ──────────────────────────────────────────────────────────────
    function renderStudyVault(d) {
        return d.study_vault.map(section => `
  <div style="${glass('margin-bottom:14px;overflow:hidden')}">
    <div style="padding:14px 18px;display:flex;align-items:center;justify-content:space-between;cursor:pointer" onclick="toggleCC('sv-${section.id}')">
      <div style="display:flex;align-items:center;gap:12px">
        <span style="font-size:22px">${section.icon}</span>
        <div>
          <div style="font-size:14px;font-weight:700;color:${C.textP}">${section.title}</div>
          <div style="font-size:11px;color:${C.textM}">${section.category} · Exams: ${section.exam_map.join(', ')}</div>
        </div>
      </div>
      <div style="display:flex;align-items:center;gap:8px">
        <span style="padding:2px 10px;border-radius:12px;font-size:10px;font-weight:800;background:${section.weight === 'CRITICAL' ? C.rose + '18' : section.weight === 'HIGH' ? C.amber + '18' : C.cyan + '18'};color:${section.weight === 'CRITICAL' ? C.rose : section.weight === 'HIGH' ? C.amber : C.cyan};border:1px solid currentColor">${section.weight}</span>
        <span id="sv-icon-${section.id}" style="color:${C.textM}">▼</span>
      </div>
    </div>
    <div id="sv-${section.id}" style="display:none;border-top:1px solid ${C.bs}">
      ${section.content.map(sub => `
      <div style="padding:14px 18px;border-bottom:1px solid ${C.bs}">
        <div style="font-size:12px;font-weight:700;color:${C.indigo};margin-bottom:8px">${sub.h}</div>
        <pre style="font-size:11px;color:${C.textS};line-height:1.7;white-space:pre-wrap;font-family:inherit;margin:0">${sub.body}</pre>
      </div>`).join('')}
    </div>
  </div>`).join('');
    }

    // ── ACTION PLAN ──────────────────────────────────────────────────────────────
    function renderActionPlan(d) {
        return `
  <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:14px">
    ${d.action_plan.map(w => `
    <div style="${glass('padding:18px 20px;border-left:3px solid ' + w.color)}">
      <div style="font-size:10px;font-weight:800;color:${w.color};text-transform:uppercase;letter-spacing:.08em;margin-bottom:4px">${w.week} · ${w.priority}</div>
      <div style="font-size:14px;font-weight:700;color:${C.textP};margin-bottom:12px">${w.title}</div>
      ${w.tasks.map(t => `
      <div style="display:flex;gap:8px;align-items:flex-start;padding:6px 0;border-bottom:1px solid ${C.bs}">
        <div style="width:16px;height:16px;border-radius:4px;border:2px solid ${w.color};flex-shrink:0;margin-top:1px;cursor:pointer" onclick="this.style.background='${w.color}';this.innerHTML='✓';this.style.color='#fff';this.style.fontSize='10px';this.style.display='flex';this.style.alignItems='center';this.style.justifyContent='center'"></div>
        <div style="font-size:12px;color:${C.textS};line-height:1.5">${t}</div>
      </div>`).join('')}
    </div>`).join('')}
  </div>`;
    }

    // ── Shared toggle ────────────────────────────────────────────────────────────
    window.toggleCC = function (id) {
        const el = $(id); if (!el) return;
        const open = el.style.display !== 'none';
        el.style.display = open ? 'none' : '';
        const icon = $('sv-icon-' + id.replace('sv-', ''));
        if (icon) icon.textContent = open ? '▼' : '▲';
    };

    // ── Wire into profile switch ─────────────────────────────────────────────────
    (function () {
        const boot = () => {
            if (typeof CAREER_INTELLIGENCE === 'undefined' || typeof USER_PROFILES === 'undefined') {
                setTimeout(boot, 200); return;
            }
            if ($('careerCenterRoot')) window.renderCareerCenter();
        };
        if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
        else boot();

        // Patch switchProfile to re-render
        const _wait = () => {
            if (typeof switchProfile === 'undefined') { setTimeout(_wait, 200); return; }
            const _prev = window.switchProfile;
            window.switchProfile = function (id) {
                _prev && _prev(id);
                setTimeout(() => { if ($('careerCenterRoot')) window.renderCareerCenter(); }, 120);
            };
        };
        _wait();
    })();

})(); // IIFE end
