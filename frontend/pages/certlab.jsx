/**
 * CertLab — Standalone Certification Prep Lab
 *
 * Separate page from main dashboard. Same JWT auth (localStorage "token").
 * Routes to /certlab — links from Study Vault tab and header nav.
 *
 * Features:
 *   - Cert + artifact type + domain selector
 *   - 3-node ArtifactSovereignAgent pipeline with live progress
 *   - Full artifact viewer: study sections, practice exam with distractor logic
 *   - Fidelity score badge (Quality: X/100) on every artifact
 *   - Session history (localStorage, per user, isolated by JWT)
 *   - Global Help Sidebar (same definitions as main dashboard)
 */
import { useEffect, useState, useRef, useCallback } from "react";
import { useRouter } from "next/router";
import axios from "axios";

const API = process.env.NEXT_PUBLIC_API_URL || "https://cert-navigator-production.up.railway.app";

// ─── Design tokens (matches main dashboard Gold Standard) ─────────────────
const C = {
  bgPrimary:   "#0a0b14",
  bgSecondary: "#12131f",
  bgTertiary:  "#1a1b2e",
  bgGlass:     "rgba(18,19,31,0.75)",
  textPrimary: "#e8e9f3",
  textSec:     "#9ca3b8",
  textMuted:   "#5f6580",
  indigo:      "#6366f1",
  cyan:        "#06b6d4",
  purple:      "#a855f7",
  amber:       "#f59e0b",
  emerald:     "#10b981",
  rose:        "#f43f5e",
  borderSub:   "rgba(99,102,241,0.12)",
  borderMed:   "rgba(99,102,241,0.25)",
  gradPrimary: "linear-gradient(135deg,#6366f1,#06b6d4)",
  gradCool:    "linear-gradient(135deg,#a855f7,#6366f1)",
};

const glass = {
  background:          C.bgGlass,
  backdropFilter:      "blur(12px)",
  WebkitBackdropFilter:"blur(12px)",
  border:              `1px solid ${C.borderSub}`,
  borderRadius:        16,
};

function authHeader() {
  const t = typeof window !== "undefined" ? localStorage.getItem("token") : null;
  return t ? { Authorization: `Bearer ${t}` } : {};
}

// ─── Error string extractor — prevents "Objects are not valid as React child" ─
function _errMsg(e) {
  if (!e) return "";
  if (typeof e === "string") return e;
  if (Array.isArray(e)) return e.map(x => (typeof x === "object" ? (x?.msg || x?.message || JSON.stringify(x)) : String(x))).join("; ");
  if (typeof e === "object") return e.msg || e.message || e.detail || e.error || JSON.stringify(e);
  return String(e);
}

// ─── Help Sidebar definitions ──────────────────────────────────────────────
const HELP_DEFS = [
  { term: "Fidelity Score", def: "Quality measure (0–100) of a generated artifact. Cross-references content coverage against official domain weightings. Agent retries generation up to 3× until score ≥ 90.", formula: "Fidelity = domains_covered/total × content_depth × question_accuracy" },
  { term: "Study Guide", def: "26-section deep-dive per cert. Covers all exam domains with conceptual explanations, real-world examples, and strategy tips. Best for first-pass learning.", formula: "Sections ∝ domain_weight_pct × cert complexity" },
  { term: "Cheat Sheet", def: "8-section high-density reference. Domain weights, key formulas, and exam traps. Best for final review 48h before exam.", formula: "1 section per major domain + exam strategy" },
  { term: "Practice Exam", def: "10 adversarial MCQs with Distractor Logic. Each wrong answer explains why it's wrong (not just why the right answer is right). Targets 90% readiness.", formula: "Difficulty adapts: medium → hard after 3 correct, → easy after 3 wrong" },
  { term: "Distractor Logic", def: "Explanation of why each wrong option was crafted the way it was — exposing common exam traps and knowledge gaps that examiners exploit.", formula: "Based on documented CISA/AIGP candidate error patterns" },
  { term: "Domain Filter", def: "Generate an artifact focused on a single exam domain (e.g. 'Information Asset Security' for CISA). Useful for targeted gap-filling after a practice exam.", formula: "Narrows corpus_sections to selected domain only" },
  { term: "Research Node", def: "First pipeline stage: loads the knowledge corpus for the selected cert and domain. Extracts domain weighting from official exam outlines.", formula: "Corpus = official_domains + weighted_topic_map" },
  { term: "Synthesis Node", def: "Second pipeline stage: assembles structured content from the corpus. Applies domain weighting to determine section depth.", formula: "Section_depth ∝ domain_weight_pct" },
  { term: "Adversarial Node", def: "Third pipeline stage: generates practice questions with distractors. Reviews fidelity against domain standards. Retries synthesis if fidelity < 90.", formula: "Loop: generate → score → refine until fidelity ≥ 90 or attempts = 3" },
];

// ─── Main Component ───────────────────────────────────────────────────────
export default function CertLab() {
  const router = useRouter();

  const [user,             setUser]             = useState(null);
  const [catalog,          setCatalog]          = useState(null);
  const [selectedCert,     setSelectedCert]     = useState(null);
  const [selectedType,     setSelectedType]     = useState("study_guide");
  const [selectedDomains,  setSelectedDomains]  = useState([]);  // multi-select
  const [generating,       setGenerating]       = useState(false);
  const [progress,         setProgress]         = useState({ pct: 0, stage: "" });
  const [artifact,         setArtifact]         = useState(null);
  const [error,            setError]            = useState("");
  const [helpOpen,         setHelpOpen]         = useState(false);
  const [sessionHistory,   setSessionHistory]   = useState([]);
  const [activeQuestion,   setActiveQuestion]   = useState(0);
  const [answered,         setAnswered]         = useState({});
  const [expandedSec,      setExpandedSec]      = useState({});
  const [etcLeft,          setEtcLeft]          = useState(0);
  const [architectRecs,    setArchitectRecs]    = useState(null);
  // Verified Credentials widget state
  const [newCert,          setNewCert]          = useState("");
  const [certSaving,       setCertSaving]       = useState(false);
  const [localCerts,       setLocalCerts]       = useState([]);
  const wsRef   = useRef(null);
  const etcRef  = useRef(null);

  // ── Auto-select first cert when catalog loads ────────────────────────────
  useEffect(() => {
    if (catalog?.certifications?.length && !selectedCert) {
      setSelectedCert(catalog.certifications[0].id);
    }
  }, [catalog]);

  // ── Auto-expand first 2 sections after artifact generates ─────────────────
  useEffect(() => {
    if (artifact?.sections?.length) {
      setExpandedSec({ 0: true, 1: true });
    }
  }, [artifact]);

  // ── ETC countdown — starts when generating=true, counts down to 0 ────────
  useEffect(() => {
    if (generating) {
      setEtcLeft(calcEtcSecs);
      etcRef.current = setInterval(() => {
        setEtcLeft(s => (s <= 1 ? (clearInterval(etcRef.current), 0) : s - 1));
      }, 1000);
    } else {
      clearInterval(etcRef.current);
      setEtcLeft(0);
    }
    return () => clearInterval(etcRef.current);
  }, [generating]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Auth gate ────────────────────────────────────────────────────────────
  useEffect(() => {
    const headers = authHeader();
    if (!headers.Authorization) { router.push("/login"); return; }

    // Fetch user profile + profile-driven certlab config + architect recs in parallel
    Promise.all([
      axios.get(`${API}/users/me`,                { headers }),
      axios.get(`${API}/api/certlab/config`,      { headers }),
      axios.get(`${API}/api/architect/analyze`,   { headers }).catch(() => null),
    ]).then(([meRes, cfgRes, archRes]) => {
      setUser(meRes.data);
      setCatalog(cfgRes.data);
      if (archRes?.data?.recommendations?.length) {
        setArchitectRecs(archRes.data);
      }
      // Populate Verified Credentials from profile
      const profileCerts = meRes.data?.profile?.certifications || [];
      setLocalCerts(profileCerts.map(c => (typeof c === "string" ? c : c.name)).filter(Boolean));
    }).catch(() => {
      axios.get(`${API}/users/me`, { headers })
        .then(r => {
          setUser(r.data);
          const profileCerts = r.data?.profile?.certifications || [];
          setLocalCerts(profileCerts.map(c => (typeof c === "string" ? c : c.name)).filter(Boolean));
        })
        .catch(() => { localStorage.removeItem("token"); router.push("/login"); });
    });

    // Load session history from localStorage
    try {
      const raw = localStorage.getItem("certlab_history");
      if (raw) setSessionHistory(JSON.parse(raw));
    } catch {}
  }, []);

  // Domain-specific lab type labels
  const DOMAIN_LAB_LABELS = {
    research_academia: { study_guide:"Research Methods Lab", cheat_sheet:"Protocol Quick-Ref",  practice_exam:"IRB Simulation"   },
    data_science:      { study_guide:"ML Study Lab",         cheat_sheet:"Model Quick-Ref",     practice_exam:"DS Exam Sim"       },
    it_audit:          { study_guide:"Audit Lab",            cheat_sheet:"Controls Quick-Ref",  practice_exam:"Audit Simulation"  },
    healthcare:        { study_guide:"Clinical Study Lab",   cheat_sheet:"Care Quick-Ref",      practice_exam:"Clinical Sim"      },
    finance:           { study_guide:"Finance Study Lab",    cheat_sheet:"Quant Quick-Ref",     practice_exam:"CFA/FRM Sim"       },
    engineering:       { study_guide:"Engineering Lab",      cheat_sheet:"Systems Quick-Ref",   practice_exam:"Dev Sim"           },
    product:           { study_guide:"PM Study Lab",         cheat_sheet:"PM Quick-Ref",        practice_exam:"Agile Sim"         },
  };
  const domainLabels = DOMAIN_LAB_LABELS[catalog?.domain] || {};

  // Domain-aware cert list — populated from API, never hardcoded for specific people
  const certs = (catalog?.certifications?.length ? catalog.certifications : [
    { id:"aigp",  acronym:"AIGP",  name:"AI Governance Professional",           study_weeks:"8–12 weeks",  prebuilt:false, domains:[] },
    { id:"cisa",  acronym:"CISA",  name:"Certified Information Systems Auditor", study_weeks:"16–20 weeks", prebuilt:false, domains:[] },
    { id:"aaia",  acronym:"AAIA",  name:"Associate AI Auditor",                  study_weeks:"6–10 weeks",  prebuilt:true,  domains:[] },
    { id:"ciasp", acronym:"CIASP", name:"Certified Internal Audit Specialist",   study_weeks:"8–12 weeks",  prebuilt:true,  domains:[] },
  ]);

  // Artifact generation time — from API if available
  const TYPE_META = catalog?.type_meta || {
    study_guide:       { label:"Study Guide",       gen_secs:"45–90s",  gen_secs_max:90,  study_time:"2–4 weeks"  },
    cheat_sheet:       { label:"Cheat Sheet",        gen_secs:"20–40s",  gen_secs_max:40,  study_time:"2–4 hours"  },
    practice_exam:     { label:"Practice Exam",      gen_secs:"30–60s",  gen_secs_max:60,  study_time:"1–2 hours"  },
    practical_labwork: { label:"Practical Labwork",  gen_secs:"60–120s", gen_secs_max:120, study_time:"4–8 hours"  },
  };

  const types = [
    { id:"study_guide",       label:"Study Guide",       ...TYPE_META.study_guide       },
    { id:"cheat_sheet",       label:"Cheat Sheet",        ...TYPE_META.cheat_sheet       },
    { id:"practice_exam",     label:"Practice Exam",      ...TYPE_META.practice_exam     },
    { id:"practical_labwork", label:"Practical Labwork",  ...TYPE_META.practical_labwork },
  ];

  const selectedCertObj = certs.find(c => c.id === selectedCert);

  // ── Multi-select domain helpers ────────────────────────────────────────────
  const toggleDomain = id =>
    setSelectedDomains(prev =>
      prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]
    );

  // Dynamic ETC calculation shown BEFORE clicking Generate
  const ETC_BASE = { study_guide: 60, cheat_sheet: 30, practice_exam: 45, practical_labwork: 90 };
  const domainCount = selectedDomains.length || (selectedCertObj?.domains?.length || 1);
  const extraDomains = Math.max(0, domainCount - 1);
  const calcEtcSecs = (ETC_BASE[selectedType] || 60) + (extraDomains * 20);

  const _delay = ms => new Promise(r => setTimeout(r, ms));

  const handleGenerateWith = (certId, type) => {
    if (!certId || !type) return;
    setSelectedCert(certId);
    setSelectedType(type);
    setSelectedDomains([]);
    setArtifact(null);
    setAnswered({});
    setExpandedSec({});
    setActiveQuestion(0);
    setError("");
    // Trigger via ref after state updates settle
    setTimeout(() => _triggerGenerate(certId, type), 0);
  };

  const _triggerGenerate = async (certId, type) => {
    if (!certId || !type) return;
    setGenerating(true);
    setProgress({ pct: 5, stage: "Research Node: Loading knowledge corpus…" });
    const headers = authHeader();
    try {
      const { data } = await axios.post(
        `${API}/api/artifacts/generate`,
        { cert_id: certId, artifact_type: type || "study_guide" },
        { headers },
      );
      // Note: _triggerGenerate is used by suggested labs (no domain filter needed)
      if (data.status === "complete" && data.artifact) {
        setProgress({ pct: 30, stage: "Research Node: Corpus loaded…" });
        await _delay(280);
        setProgress({ pct: 62, stage: "Synthesis Node: Assembling content…" });
        await _delay(280);
        setProgress({ pct: 87, stage: "Adversarial Node: Generating questions…" });
        await _delay(280);
        setProgress({ pct: 100, stage: "Complete — fidelity verified." });
        setArtifact(data.artifact);
        setGenerating(false);
        const entry = {
          id: Date.now(), cert: data.artifact?.cert_acronym || certId.toUpperCase(),
          type, fidelity: data.artifact?.fidelity_score ?? data.fidelity_score,
          timestamp: new Date().toISOString(),
        };
        setSessionHistory(prev => {
          const next = [entry, ...prev].slice(0, 10);
          try { localStorage.setItem("certlab_history", JSON.stringify(next)); } catch {}
          return next;
        });
      } else {
        throw new Error(data.error || "Generation failed");
      }
    } catch (err) {
      setError(_errMsg(err.response?.data?.detail) || err.message || "Generation failed");
      setProgress({ pct: 0, stage: "" });
      setGenerating(false);
    }
  };

  const handleGenerate = async () => {
    if (!selectedCert || !selectedType) return;
    setGenerating(true);
    setArtifact(null);
    setAnswered({});
    setExpandedSec({});
    setActiveQuestion(0);
    setError("");
    setProgress({ pct: 5, stage: "Research Node: Loading knowledge corpus…" });

    const headers = authHeader();
    try {
      const domainPayload =
        selectedDomains.length === 1 ? { domain_id: selectedDomains[0] } :
        selectedDomains.length > 1  ? { domain_ids: selectedDomains } :
        {};
      const { data } = await axios.post(
        `${API}/api/artifacts/generate`,
        { cert_id: selectedCert, artifact_type: selectedType || "study_guide", ...domainPayload },
        { headers },
      );

      if (data.status === "complete" && data.artifact) {
        setProgress({ pct: 30, stage: "Research Node: Corpus loaded…" });
        await _delay(280);
        setProgress({ pct: 62, stage: "Synthesis Node: Assembling content…" });
        await _delay(280);
        setProgress({ pct: 87, stage: "Adversarial Node: Generating questions…" });
        await _delay(280);
        setProgress({ pct: 100, stage: "Complete — fidelity verified." });
        setArtifact(data.artifact);
        setGenerating(false);

        // Persist to session history (localStorage)
        const entry = {
          id:        Date.now(),
          cert:      data.artifact?.cert_acronym || selectedCert.toUpperCase(),
          type:      selectedType,
          fidelity:  data.artifact?.fidelity_score ?? data.fidelity_score,
          timestamp: new Date().toISOString(),
        };
        setSessionHistory(prev => {
          const next = [entry, ...prev].slice(0, 10);
          try { localStorage.setItem("certlab_history", JSON.stringify(next)); } catch {}
          return next;
        });
      } else if (data.status === "queued" && data.ws_url) {
        _connectWebSocket(data.ws_url.replace("/ws/", `ws://${window.location.hostname}:8001/ws/`));
      } else {
        throw new Error(data.error || "Generation failed");
      }
    } catch (err) {
      setError(_errMsg(err.response?.data?.detail) || err.message || "Generation failed");
      setProgress({ pct: 0, stage: "" });
      setGenerating(false);
    }
  };

  const _connectWebSocket = wsUrl => {
    if (wsRef.current) wsRef.current.close();
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;
    ws.onmessage = e => {
      const msg = JSON.parse(e.data);
      setProgress({ pct: msg.progress_pct || 0, stage: msg.stage || "" });
      if (msg.state === "SUCCESS" && msg.result?.artifact) {
        setArtifact(msg.result.artifact);
        setGenerating(false);
        ws.close();
      } else if (["FAILURE","TIMEOUT"].includes(msg.state)) {
        setError(msg.stage || "Generation failed.");
        setGenerating(false);
        ws.close();
      }
    };
    ws.onerror = () => { setError("WebSocket error."); setGenerating(false); };
  };

  const handleAnswer = (qIdx, optIdx) => {
    if (answered[qIdx] !== undefined) return;
    setAnswered(prev => ({ ...prev, [qIdx]: optIdx }));
  };

  const correctCount  = artifact?.questions?.filter((q, i) => answered[i] === q.correct_index).length || 0;
  const totalAnswered = Object.keys(answered).length;
  const fidelity      = artifact?.fidelity_score;
  const fidelityColor = fidelity >= 90 ? C.emerald : fidelity >= 75 ? C.amber : C.rose;

  if (!user) {
    return (
      <div style={{ background:C.bgPrimary, height:"100vh", display:"flex", alignItems:"center", justifyContent:"center" }}>
        <div style={{ textAlign:"center" }}>
          <div style={{ width:40, height:40, border:`3px solid rgba(99,102,241,0.2)`, borderTop:`3px solid ${C.indigo}`, borderRadius:"50%", animation:"spin 1s linear infinite", margin:"0 auto 16px" }} />
          <div style={{ fontSize:14, color:C.textSec }}>Loading CertLab…</div>
        </div>
      </div>
    );
  }

  return (
    <div style={{ background:C.bgPrimary, minHeight:"100vh", fontFamily:"'Segoe UI',system-ui,sans-serif", color:C.textPrimary }}>
      {/* Ambient orbs */}
      <div style={{ position:"fixed", inset:0, overflow:"hidden", pointerEvents:"none", zIndex:0 }}>
        <div style={{ position:"absolute", top:"-150px", left:"-150px", width:500, height:500, borderRadius:"50%", background:"rgba(168,85,247,0.12)", filter:"blur(100px)" }} />
        <div style={{ position:"absolute", bottom:"-100px", right:"-100px", width:400, height:400, borderRadius:"50%", background:"rgba(6,182,212,0.1)", filter:"blur(100px)" }} />
      </div>

      <div style={{ position:"relative", zIndex:1 }}>
        {/* ── Header ── */}
        <header style={{ ...glass, borderRadius:0, padding:"12px 28px", display:"flex", alignItems:"center", justifyContent:"space-between", borderBottom:`1px solid ${C.borderSub}`, position:"sticky", top:0, zIndex:100 }}>
          <div style={{ display:"flex", alignItems:"center", gap:14 }}>
            <div style={{ width:36, height:36, borderRadius:10, background:C.gradCool, display:"flex", alignItems:"center", justifyContent:"center", fontSize:18, fontWeight:800 }}>L</div>
            <div>
              <div style={{ fontWeight:700, fontSize:16, color:C.textPrimary }}>CertLab</div>
              <div style={{ fontSize:11, color:C.textMuted }}>Certification Prep — Agentic · 90% Fidelity</div>
            </div>
          </div>
          <div style={{ display:"flex", alignItems:"center", gap:10 }}>
            <span style={{ fontSize:12, color:C.textMuted }}>
              {user.full_name || user.email}
            </span>
            <a href="/dashboard" style={{ padding:"6px 14px", borderRadius:8, border:`1px solid ${C.borderSub}`, color:C.textSec, textDecoration:"none", fontSize:13 }}>
              Dashboard
            </a>
            <button onClick={(e) => toggleDomain(e.target.innerText)}
              style={{ padding:"6px 14px", borderRadius:8, border:`1px solid rgba(244,63,94,0.3)`, background:"transparent", color:C.rose, cursor:"pointer", fontSize:13 }}>
              Sign Out
            </button>
          </div>
        </header>

        {/* ── Help Sidebar ── */}
        <LabHelpSidebar open={helpOpen} onClose={() => setHelpOpen(false)} />
        <button onClick={(e) => toggleDomain(e.target.innerText)} title="Field definitions & help"
          style={{ position:"fixed", bottom:28, right:28, zIndex:200, width:48, height:48, borderRadius:"50%",
            background:C.gradCool, border:"none", cursor:"pointer", boxShadow:"0 4px 20px rgba(168,85,247,0.5)",
            fontSize:20, display:"flex", alignItems:"center", justifyContent:"center", color:"#fff", fontWeight:700 }}>
          ?
        </button>

        {/* ── Main layout: sidebar + content ── */}
        <div style={{ display:"grid", gridTemplateColumns:"320px 1fr", gap:0, minHeight:"calc(100vh - 61px)" }}>

          {/* ── Left sidebar: controls ── */}
          <div style={{ borderRight:`1px solid ${C.borderSub}`, padding:"24px 20px", overflowY:"auto" }}>

            {/* Suggested Labs strip */}
            {catalog?.suggested_labs?.length > 0 && (
              <div style={{ marginBottom:20 }}>
                <div style={{ fontSize:10, color:C.textMuted, textTransform:"uppercase", letterSpacing:"0.08em", fontWeight:700, marginBottom:8 }}>
                  Suggested Labs
                </div>
                <div style={{ display:"flex", flexDirection:"column", gap:6 }}>
                  {catalog.suggested_labs.map((lab, i) => (
                    <button key={i} onClick={(e) => toggleDomain(e.target.innerText)}
                      disabled={generating}
                      style={{ padding:"8px 12px", borderRadius:8, border:`1px solid rgba(168,85,247,0.25)`,
                        background:"rgba(168,85,247,0.08)", color:C.purple, cursor: generating ? "not-allowed" : "pointer",
                        textAlign:"left", fontSize:11, fontWeight:700, transition:"all 0.15s",
                        opacity: generating ? 0.5 : 1 }}>
                      {lab.label}
                      <span style={{ fontSize:9, color:C.textMuted, fontWeight:400, marginLeft:6 }}>
                        {lab.cert_id.toUpperCase()} · {lab.type.replace(/_/g," ")}
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Cert selector */}
            <div style={{ marginBottom:20 }}>
              <div style={{ fontSize:10, color:C.textMuted, textTransform:"uppercase", letterSpacing:"0.08em", fontWeight:700, marginBottom:10 }}>
                Certification
              </div>
              {/* Domain badge — shows detected profile domain */}
              {catalog?.domain_label && (
                <div style={{ fontSize:10, color:C.cyan, background:"rgba(6,182,212,0.08)", border:`1px solid rgba(6,182,212,0.2)`, borderRadius:8, padding:"4px 10px", marginBottom:8, display:"inline-block" }}>
                  Profile domain: {catalog.domain_label}
                </div>
              )}
              <div style={{ display:"flex", flexDirection:"column", gap:6 }}>
                {certs.map(c => (
                  <button key={c.id} onClick={(e) => toggleDomain(e.target.innerText)}
                    style={{ padding:"10px 14px", borderRadius:10, border:`1px solid ${selectedCert === c.id ? C.indigo : C.borderSub}`,
                      background: selectedCert === c.id ? "rgba(99,102,241,0.12)" : "transparent",
                      color: selectedCert === c.id ? C.indigo : C.textSec,
                      cursor:"pointer", textAlign:"left", transition:"all 0.15s" }}>
                    <div style={{ display:"flex", alignItems:"center", gap:6, marginBottom:2 }}>
                      <span style={{ fontSize:13, fontWeight:700 }}>{c.acronym}</span>
                      {c.prebuilt && (
                        <span style={{ fontSize:9, fontWeight:700, padding:"1px 6px", borderRadius:10, background:"rgba(16,185,129,0.15)", color:C.emerald, border:`1px solid rgba(16,185,129,0.3)` }}>
                          PRE-BUILT
                        </span>
                      )}
                      {c.priority === "critical" && !c.prebuilt && (
                        <span style={{ fontSize:9, fontWeight:700, padding:"1px 6px", borderRadius:10, background:"rgba(244,63,94,0.12)", color:C.rose, border:`1px solid rgba(244,63,94,0.25)` }}>
                          PRIORITY
                        </span>
                      )}
                    </div>
                    <div style={{ fontSize:10, color:C.textMuted }}>{c.name || c.full_name}</div>
                    {c.study_weeks && (
                      <div style={{ fontSize:9, color:C.textMuted, marginTop:3 }}>
                        Prep time: {c.study_weeks}
                      </div>
                    )}
                    {c.rationale && (
                      <div style={{ fontSize:9, color:C.textMuted, marginTop:2, fontStyle:"italic", overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" }}>
                        {c.rationale}
                      </div>
                    )}
                  </button>
                ))}
              </div>
            </div>

            {/* ── Verified Credentials widget ── */}
            <div style={{ ...glass, padding:"12px 14px", marginBottom:20, borderColor:"rgba(99,102,241,0.25)" }}>
              <div style={{ fontSize:10, color:C.textMuted, textTransform:"uppercase", letterSpacing:"0.08em", fontWeight:700, marginBottom:8 }}>
                Verified Credentials
              </div>
              {/* Detected cert chips */}
              {localCerts.length > 0 && (
                <div style={{ display:"flex", flexWrap:"wrap", gap:4, marginBottom:8 }}>
                  {localCerts.map(cert => (
                    <span key={cert} style={{ display:"inline-flex", alignItems:"center", gap:4, padding:"2px 8px",
                      borderRadius:10, background:"rgba(99,102,241,0.12)", border:`1px solid rgba(99,102,241,0.3)`,
                      color:C.indigo, fontSize:11, fontWeight:700 }}>
                      {cert}
                      <button onClick={async () => {
                          const headers = authHeader();
                          try {
                            await axios.patch(`${API}/api/profile/certifications`, { remove: [cert] }, { headers });
                            setLocalCerts(prev => prev.filter(c => c !== cert));
                          } catch {}
                        }}
                        style={{ background:"none", border:"none", color:C.rose, cursor:"pointer", fontSize:12, padding:0, lineHeight:1 }}>
                        ×
                      </button>
                    </span>
                  ))}
                </div>
              )}
              {localCerts.length === 0 && (
                <div style={{ fontSize:10, color:C.textMuted, marginBottom:8 }}>No certs detected yet.</div>
              )}
              <div style={{ fontSize:10, color:C.textMuted, marginBottom:6 }}>AI missed one?</div>
              <div style={{ display:"flex", gap:6 }}>
                <input
                  value={newCert}
                  onChange={e => setNewCert(e.target.value)}
                  onKeyDown={async e => {
                    if (e.key === "Enter" && newCert.trim()) {
                      setCertSaving(true);
                      const headers = authHeader();
                      try {
                        const res = await axios.patch(`${API}/api/profile/certifications`, { add: [newCert.trim()] }, { headers });
                        setLocalCerts(res.data.certifications || []);
                        setNewCert("");
                        // Re-fetch architect recs
                        axios.get(`${API}/api/architect/analyze`, { headers }).then(r => {
                          if (r.data?.recommendations?.length) setArchitectRecs(r.data);
                        }).catch(() => {});
                      } catch {}
                      setCertSaving(false);
                    }
                  }}
                  placeholder="e.g. CISA, PMP…"
                  style={{ flex:1, padding:"5px 10px", borderRadius:6, border:`1px solid ${C.borderMed}`,
                    background:C.bgTertiary, color:C.textPrimary, fontSize:11, outline:"none" }}
                />
                <button
                  disabled={certSaving || !newCert.trim()}
                  onClick={async () => {
                    if (!newCert.trim()) return;
                    setCertSaving(true);
                    const headers = authHeader();
                    try {
                      const res = await axios.patch(`${API}/api/profile/certifications`, { add: [newCert.trim()] }, { headers });
                      setLocalCerts(res.data.certifications || []);
                      setNewCert("");
                      axios.get(`${API}/api/architect/analyze`, { headers }).then(r => {
                        if (r.data?.recommendations?.length) setArchitectRecs(r.data);
                      }).catch(() => {});
                    } catch {}
                    setCertSaving(false);
                  }}
                  style={{ padding:"5px 10px", borderRadius:6, border:`1px solid ${C.indigo}`,
                    background: certSaving || !newCert.trim() ? C.bgTertiary : "rgba(99,102,241,0.15)",
                    color: certSaving || !newCert.trim() ? C.textMuted : C.indigo,
                    cursor: certSaving || !newCert.trim() ? "not-allowed" : "pointer",
                    fontSize:11, fontWeight:700, whiteSpace:"nowrap" }}>
                  {certSaving ? "…" : "+ Add"}
                </button>
              </div>
            </div>

            {/* Cert meta strip */}
            {selectedCertObj && (
              <div style={{ ...glass, padding:"12px 14px", marginBottom:20, display:"grid", gridTemplateColumns:"1fr 1fr", gap:8 }}>
                {[
                  ["Questions", selectedCertObj.exam_questions],
                  ["Duration",  selectedCertObj.duration_mins ? `${selectedCertObj.duration_mins}m` : "—"],
                  ["Passing",   selectedCertObj.passing_score],
                  ["Domains",   selectedCertObj.domains?.length || "—"],
                ].map(([label, val]) => (
                  <div key={label} style={{ textAlign:"center", padding:"6px 0", background:C.bgTertiary, borderRadius:6 }}>
                    <div style={{ fontSize:9, color:C.textMuted, marginBottom:2 }}>{label}</div>
                    <div style={{ fontSize:12, fontWeight:700, color:C.indigo }}>{val}</div>
                  </div>
                ))}
              </div>
            )}

            {/* Domain filter — multi-select with indigo glow */}
            {selectedCertObj?.domains?.length > 0 && (
              <div style={{ marginBottom:20 }}>
                <div style={{ fontSize:10, color:C.textMuted, textTransform:"uppercase", letterSpacing:"0.08em", fontWeight:700, marginBottom:8 }}>
                  Focus Domain <span style={{ color:C.textMuted, fontWeight:400 }}>(multi-select)</span>
                </div>
                <div style={{ display:"flex", flexWrap:"wrap", gap:6 }}>
                  <button onClick={(e) => toggleDomain(e.target.innerText)}
                    style={{ padding:"4px 10px", borderRadius:6,
                      border:`1px solid ${selectedDomains.length === 0 ? C.cyan : C.borderSub}`,
                      background: selectedDomains.length === 0 ? "rgba(6,182,212,0.1)" : "transparent",
                      color: selectedDomains.length === 0 ? C.cyan : C.textMuted, cursor:"pointer", fontSize:10 }}>
                    All
                  </button>
                  {selectedCertObj.domains.map(d => {
                    const active = selectedDomains.includes(d.id);
                    return (
                      <button key={d.id} onClick={(e) => toggleDomain(e.target.innerText)}
                        style={{ padding:"4px 10px", borderRadius:6,
                          border:`1px solid ${active ? C.indigo : C.borderSub}`,
                          background: active ? "rgba(99,102,241,0.15)" : "transparent",
                          boxShadow: active ? "0 0 8px rgba(99,102,241,0.35)" : "none",
                          color: active ? C.indigo : C.textMuted,
                          cursor:"pointer", fontSize:10, transition:"all 0.15s" }}>
                        {d.name}
                      </button>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Artifact type */}
            <div style={{ marginBottom:20 }}>
              <div style={{ fontSize:10, color:C.textMuted, textTransform:"uppercase", letterSpacing:"0.08em", fontWeight:700, marginBottom:8 }}>
                Artifact Type
              </div>
              <div style={{ display:"flex", flexDirection:"column", gap:6 }}>
                {types.map(t => (
                  <button key={t.id} onClick={(e) => toggleDomain(e.target.innerText)}
                    style={{ padding:"10px 14px", borderRadius:10, border:`1px solid ${selectedType === t.id ? C.indigo : C.borderSub}`,
                      background: selectedType === t.id ? C.gradPrimary : "transparent",
                      color: selectedType === t.id ? "#fff" : C.textSec,
                      cursor:"pointer", textAlign:"left", transition:"all 0.15s" }}>
                    <div style={{ fontSize:12, fontWeight:700 }}>{domainLabels[t.id] || t.label}</div>
                    <div style={{ fontSize:10, opacity:0.8, marginTop:1 }}>{t.desc}</div>
                    <div style={{ fontSize:9, opacity:0.65, marginTop:2 }}>
                      Gen: {t.gen_secs} · Study: {t.study_time}
                    </div>
                  </button>
                ))}
              </div>
            </div>

            {/* Pre-built interactive lab shortcut (any cert with prebuilt flag) */}
            {selectedCert && certs.find(c => c.id === selectedCert)?.prebuilt && (
              <div style={{ ...glass, padding:"12px 14px", marginBottom:16, borderColor:"rgba(16,185,129,0.3)" }}>
                <div style={{ fontSize:11, fontWeight:700, color:C.emerald, marginBottom:4 }}>
                  Pre-built Interactive Lab available
                </div>
                <div style={{ fontSize:10, color:C.textMuted, marginBottom:10 }}>
                  {selectedCert.toUpperCase()} has a full interactive simulation lab with guided steps, mock exams, and compliance checklists — already built to the maximum reference depth.
                </div>
                <a href="/certlab-static.html" target="_blank" rel="noopener noreferrer"
                  style={{ display:"block", padding:"8px 0", borderRadius:7, background:"rgba(16,185,129,0.12)", border:`1px solid rgba(16,185,129,0.3)`, color:C.emerald, textAlign:"center", fontSize:11, fontWeight:700, textDecoration:"none" }}>
                  Open Interactive Lab
                </a>
              </div>
            )}

            {/* Dynamic ETC display + Generate button */}
            {!generating && selectedCert && selectedType && (
              <div style={{ fontSize:10, color:C.textMuted, textAlign:"center", marginBottom:6 }}>
                Est. ~{calcEtcSecs}s for {domainCount} domain(s) · Targets 90%+
              </div>
            )}
            <button onClick={(e) => toggleDomain(e.target.innerText)}
              title={!["aigp","cisa","ccsp"].includes(selectedCert) ? "Full labs coming for this cert" : undefined}
              style={{ width:"100%", padding:"13px", borderRadius:10, border:"none",
                background: !selectedCert || generating ? C.bgTertiary : C.gradPrimary,
                color: !selectedCert || generating ? C.textMuted : "#fff",
                cursor: !selectedCert || generating ? "not-allowed" : "pointer",
                fontSize:14, fontWeight:700, transition:"all 0.2s", marginBottom:16 }}>
              {generating ? "Generating…" : (
                `Generate ${types.find(t=>t.id===selectedType)?.label || ""}` +
                (selectedDomains.length > 1 ? ` (${selectedDomains.length} domains)` : "")
              )}
            </button>

            {error && (
              <div style={{ padding:"10px 14px", borderRadius:8, background:"rgba(244,63,94,0.1)", border:`1px solid ${C.rose}`, color:C.rose, fontSize:12, marginBottom:16 }}>
                {_errMsg(error)}
              </div>
            )}

            {/* Session history */}
            {sessionHistory.length > 0 && (
              <div>
                <div style={{ fontSize:10, color:C.textMuted, textTransform:"uppercase", letterSpacing:"0.08em", fontWeight:700, marginBottom:8 }}>
                  Recent Sessions
                </div>
                {sessionHistory.slice(0,5).map(h => (
                  <div key={h.id} style={{ padding:"8px 12px", borderRadius:8, border:`1px solid ${C.borderSub}`, marginBottom:6, display:"flex", justifyContent:"space-between", alignItems:"center" }}>
                    <div>
                      <div style={{ fontSize:11, fontWeight:700, color:C.textPrimary }}>{h.cert} · {h.type.replace(/_/g," ")}</div>
                      <div style={{ fontSize:10, color:C.textMuted }}>{new Date(h.timestamp).toLocaleDateString()}</div>
                    </div>
                    {h.fidelity != null && (
                      <span style={{ fontSize:10, fontWeight:700, color: h.fidelity >= 90 ? C.emerald : h.fidelity >= 75 ? C.amber : C.rose }}>
                        {h.fidelity}/100
                      </span>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* ── Right content area ── */}
          <div style={{ padding:"24px 28px 48px", overflowY:"auto" }}>

            {/* Progress bar with ETC countdown and Certification Pillar stepping */}
            {generating && (
              <div style={{ ...glass, padding:"20px 24px", marginBottom:20 }}>
                <div style={{ display:"flex", justifyContent:"space-between", marginBottom:8 }}>
                  <span style={{ fontSize:12, color:C.textSec, flex:1, paddingRight:12 }}>{progress.stage}</span>
                  <div style={{ display:"flex", alignItems:"center", gap:12, flexShrink:0 }}>
                    {etcLeft > 0 && (
                      <span style={{ fontSize:11, color:C.amber, fontWeight:700, background:"rgba(245,158,11,0.1)", padding:"2px 10px", borderRadius:20, border:"1px solid rgba(245,158,11,0.25)" }}>
                        ETC: {etcLeft}s
                      </span>
                    )}
                    <span style={{ fontSize:12, fontWeight:700, color:C.purple }}>{progress.pct}%</span>
                  </div>
                </div>
                <div style={{ height:6, background:C.bgTertiary, borderRadius:3, overflow:"hidden" }}>
                  <div style={{ height:"100%", width:`${progress.pct}%`, background:C.gradCool, borderRadius:3, transition:"width 0.5s ease" }} />
                </div>
                {/* Pipeline node stepping */}
                <div style={{ display:"flex", justifyContent:"space-between", marginTop:10, fontSize:10 }}>
                  {["Research Node","Synthesis Node","Adversarial Node","Fidelity Review"].map((s,i) => (
                    <span key={i} style={{ color: progress.pct >= (i+1)*25 ? C.purple : C.textMuted, fontWeight: progress.pct >= (i+1)*25 ? 700 : 400 }}>
                      {s}
                    </span>
                  ))}
                </div>
                {/* Cert domain pillars */}
                {certs.find(c => c.id === selectedCert)?.domains?.length > 0 && (
                  <div style={{ marginTop:10, borderTop:`1px solid ${C.borderSub}`, paddingTop:8 }}>
                    <div style={{ fontSize:9, color:C.textMuted, marginBottom:5, textTransform:"uppercase", letterSpacing:"0.06em" }}>
                      Certification Pillars
                    </div>
                    <div style={{ display:"flex", flexWrap:"wrap", gap:4 }}>
                      {certs.find(c => c.id === selectedCert).domains.map((d, i) => {
                        // Each pillar becomes active as progress crosses its threshold
                        const threshold = Math.round((i + 1) / certs.find(c => c.id === selectedCert).domains.length * 80);
                        const active = progress.pct >= threshold;
                        return (
                          <span key={d.id} style={{
                            fontSize:9, padding:"2px 8px", borderRadius:20, transition:"all 0.4s",
                            background: active ? "rgba(168,85,247,0.18)" : C.bgTertiary,
                            color: active ? C.purple : C.textMuted,
                            border: `1px solid ${active ? "rgba(168,85,247,0.4)" : C.borderSub}`,
                            fontWeight: active ? 700 : 400,
                          }}>
                            {active ? "✓ " : ""}{d.name.split(" ").slice(0, 3).join(" ")}
                          </span>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Artifact viewer */}
            {artifact && !generating && (
              <div>
                {/* Artifact header */}
                <div style={{ ...glass, padding:"16px 24px", marginBottom:20, display:"flex", justifyContent:"space-between", alignItems:"center", flexWrap:"wrap", gap:10 }}>
                  <div>
                    <div style={{ fontSize:18, fontWeight:700, color:C.textPrimary }}>{artifact.title}</div>
                    <div style={{ fontSize:11, color:C.textMuted, marginTop:3 }}>
                      {artifact.metadata?.domains_covered?.length || 0} domains covered
                      {artifact.generated_at ? ` · Generated ${new Date(artifact.generated_at).toLocaleTimeString()}` : ""}
                    </div>
                  </div>
                  <div style={{ display:"flex", gap:8, flexWrap:"wrap", alignItems:"center" }}>
                    {fidelity != null && (
                      <div style={{ padding:"5px 14px", borderRadius:20, fontSize:12, fontWeight:700,
                        background: `${fidelityColor}18`, color: fidelityColor, border: `1px solid ${fidelityColor}50` }}>
                        Quality: {fidelity}/100
                      </div>
                    )}
                    <div style={{ padding:"5px 14px", borderRadius:20, background:"rgba(99,102,241,0.12)", color:C.indigo, fontSize:12, fontWeight:700 }}>
                      {artifact.cert_acronym}
                    </div>
                    <div style={{ padding:"5px 14px", borderRadius:20, background:"rgba(6,182,212,0.12)", color:C.cyan, fontSize:12, fontWeight:700 }}>
                      {artifact.type?.replace(/_/g," ")}
                    </div>
                  </div>
                </div>

                {/* Study sections */}
                {artifact.sections?.length > 0 && (
                  <div style={{ marginBottom:24 }}>
                    <div style={{ fontSize:12, fontWeight:700, color:C.textMuted, textTransform:"uppercase", letterSpacing:"0.06em", marginBottom:12 }}>
                      Study Sections ({artifact.sections.length})
                    </div>
                    {artifact.sections.map((sec, i) => (
                      <div key={i} style={{ ...glass, marginBottom:8, overflow:"hidden" }}>
                        <button onClick={(e) => toggleDomain(e.target.innerText)}
                          style={{ width:"100%", padding:"14px 20px", background:"transparent", border:"none", cursor:"pointer",
                            display:"flex", justifyContent:"space-between", alignItems:"center", textAlign:"left" }}>
                          <span style={{ fontSize:13, fontWeight:700,
                            color: sec.type === "overview" ? C.indigo
                              : sec.type === "warning" || sec.type === "strategy" ? C.amber
                              : sec.type === "trips_and_traps" ? C.rose
                              : sec.type === "cross_map" ? C.cyan
                              : sec.type === "lab_scenario" ? C.emerald
                              : C.textPrimary }}>
                            {sec.heading}
                          </span>
                          <span style={{ fontSize:12, color:C.textMuted, flexShrink:0 }}>{expandedSec[i] ? "▲" : "▼"}</span>
                        </button>
                        {expandedSec[i] && (
                          <div style={{ padding:"0 20px 16px", borderTop:`1px solid ${C.borderSub}` }}>
                            <pre style={{ margin:"12px 0 0", fontSize:12, color:C.textSec, lineHeight:1.75, whiteSpace:"pre-wrap", fontFamily:"inherit" }}>
                              {sec.content}
                            </pre>
                            {sec.weight_pct && (
                              <div style={{ marginTop:8, display:"inline-block", padding:"2px 10px", borderRadius:20, background:"rgba(99,102,241,0.1)", color:C.indigo, fontSize:11 }}>
                                Exam weight: {sec.weight_pct}%
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}

                {/* Practice exam */}
                {artifact.questions?.length > 0 && (
                  <div>
                    <div style={{ fontSize:12, fontWeight:700, color:C.textMuted, textTransform:"uppercase", letterSpacing:"0.06em", marginBottom:12 }}>
                      Practice Exam ({artifact.questions.length} questions)
                    </div>

                    {/* Score banner */}
                    {totalAnswered > 0 && (
                      <div style={{ ...glass, padding:"14px 20px", marginBottom:16, display:"flex", alignItems:"center", gap:16 }}>
                        <div style={{ fontSize:14, color:C.textSec }}>
                          Score: <span style={{ fontWeight:700, color: correctCount/totalAnswered >= 0.7 ? C.emerald : C.rose }}>
                            {correctCount}/{totalAnswered} ({Math.round(correctCount/totalAnswered*100)}%)
                          </span>
                        </div>
                        {totalAnswered === artifact.questions.length && (
                          <div style={{ padding:"4px 14px", borderRadius:20, fontSize:11, fontWeight:700,
                            background: correctCount/totalAnswered >= 0.9 ? "rgba(16,185,129,0.12)" : correctCount/totalAnswered >= 0.7 ? "rgba(245,158,11,0.12)" : "rgba(244,63,94,0.12)",
                            color: correctCount/totalAnswered >= 0.9 ? C.emerald : correctCount/totalAnswered >= 0.7 ? C.amber : C.rose,
                            border: `1px solid ${correctCount/totalAnswered >= 0.9 ? C.emerald : correctCount/totalAnswered >= 0.7 ? C.amber : C.rose}` }}>
                            {correctCount/totalAnswered >= 0.9 ? "Exam Ready (90%+)" : correctCount/totalAnswered >= 0.7 ? "Near Ready" : "Needs Review"}
                          </div>
                        )}
                      </div>
                    )}

                    {/* Question nav dots */}
                    <div style={{ display:"flex", flexWrap:"wrap", gap:6, marginBottom:16 }}>
                      {artifact.questions.map((q, i) => (
                        <button key={i} onClick={(e) => toggleDomain(e.target.innerText)}
                          style={{ width:34, height:34, borderRadius:7, cursor:"pointer", fontSize:11, fontWeight:700,
                            border: `1px solid ${activeQuestion === i ? C.purple : C.borderSub}`,
                            background: answered[i] === undefined
                              ? (activeQuestion === i ? "rgba(168,85,247,0.15)" : "transparent")
                              : answered[i] === q.correct_index ? "rgba(16,185,129,0.15)" : "rgba(244,63,94,0.15)",
                            color: answered[i] === undefined
                              ? (activeQuestion === i ? C.purple : C.textMuted)
                              : answered[i] === q.correct_index ? C.emerald : C.rose }}>
                          {i+1}
                        </button>
                      ))}
                    </div>

                    {/* Active question card */}
                    {artifact.questions[activeQuestion] && (
                      <LabQuestionCard
                        question={artifact.questions[activeQuestion]}
                        qNumber={activeQuestion + 1}
                        total={artifact.questions.length}
                        answered={answered[activeQuestion]}
                        onAnswer={idx => handleAnswer(activeQuestion, idx)}
                        onNext={() => setActiveQuestion(i => Math.min(i+1, artifact.questions.length-1))}
                        onPrev={() => setActiveQuestion(i => Math.max(i-1, 0))}
                      />
                    )}
                  </div>
                )}
              </div>
            )}

            {/* Empty state — with Universal Architect Panel */}
            {!artifact && !generating && (
              <div>
                {/* Architect Panel — AI-driven cert recommendations */}
                {architectRecs?.recommendations?.length > 0 ? (
                  <div style={{ marginBottom:32 }}>
                    <div style={{ display:"flex", alignItems:"center", gap:10, marginBottom:16 }}>
                      <div style={{ width:32, height:32, borderRadius:8, background:C.gradCool, display:"flex", alignItems:"center", justifyContent:"center", fontSize:16 }}>A</div>
                      <div>
                        <div style={{ fontSize:16, fontWeight:700, color:C.textPrimary }}>Universal Architect</div>
                        <div style={{ fontSize:11, color:C.textMuted }}>
                          AI-Driven Recommendations · {architectRecs.profile_label}
                        </div>
                      </div>
                    </div>
                    {architectRecs.profile_summary && (
                      <div style={{ fontSize:11, color:C.textMuted, marginBottom:14, padding:"8px 14px", background:C.bgTertiary, borderRadius:8, borderLeft:`3px solid ${C.indigo}` }}>
                        {architectRecs.profile_summary}
                      </div>
                    )}
                    <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fit,minmax(260px,1fr))", gap:14 }}>
                      {architectRecs.recommendations.map((rec, i) => (
                        <ArchitectCard key={rec.cert_id} rec={rec} rank={i+1} onSelect={certId => {
                          setSelectedCert(certId);
                          setArtifact(null);
                        }} />
                      ))}
                    </div>
                  </div>
                ) : (
                  <div style={{ display:"flex", flexDirection:"column", alignItems:"center", justifyContent:"center", height:"30vh", textAlign:"center", marginBottom:24 }}>
                    <div style={{ width:80, height:80, borderRadius:20, background:C.gradCool, display:"flex", alignItems:"center", justifyContent:"center", fontSize:36, marginBottom:20 }}>L</div>
                    <div style={{ fontSize:22, fontWeight:700, color:C.textPrimary, marginBottom:8 }}>CertLab Ready</div>
                    <div style={{ fontSize:14, color:C.textSec, maxWidth:360, lineHeight:1.7 }}>
                      Select a certification and artifact type from the sidebar, then click Generate.
                    </div>
                  </div>
                )}

                {/* Quick-start buttons */}
                <div style={{ display:"flex", gap:12, flexWrap:"wrap", justifyContent:"center", paddingTop:8 }}>
                  {(certs.length > 0 ? certs.slice(0,4) : [
                    {id:"aigp",  acronym:"AIGP"},
                    {id:"cisa",  acronym:"CISA"},
                    {id:"ccsp",  acronym:"CCSP"},
                    {id:"aaia",  acronym:"AAIA"},
                  ]).map(c => (
                    <button key={c.id} onClick={(e) => toggleDomain(e.target.innerText)}
                      style={{ padding:"8px 20px", borderRadius:8, border:`1px solid ${C.borderMed}`, background:"transparent", color:C.indigo, cursor:"pointer", fontSize:13, fontWeight:700 }}>
                      Start {c.acronym}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Architect Card — one cert recommendation from Universal Architect ───────
function ArchitectCard({ rec, rank, onSelect }) {
  const cert         = rec.cert || {};
  const diff         = rec.difficulty_score || 5;
  const mv           = rec.market_value_score || 5;
  const diffColor    = diff <= 3 ? C.emerald : diff <= 6 ? C.amber : C.rose;
  const mvColor      = mv  >= 8 ? C.emerald : mv  >= 5 ? C.cyan  : C.textMuted;
  const rankColors   = [C.amber, C.indigo, C.textSec];
  const rankLabel    = ["#1 Recommended", "#2 Strong Fit", "#3 Path Forward"];

  return (
    <div style={{ ...glass, padding:"18px 20px", cursor:"pointer", transition:"all 0.2s", borderColor: rank === 1 ? C.indigo : undefined }}
      onClick={(e) => toggleDomain(e.target.innerText)}>
      <div style={{ display:"flex", justifyContent:"space-between", alignItems:"flex-start", marginBottom:10 }}>
        <div>
          <div style={{ fontSize:9, fontWeight:700, color:rankColors[rank-1], textTransform:"uppercase", letterSpacing:"0.06em", marginBottom:4 }}>
            {rankLabel[rank-1]}
          </div>
          <div style={{ fontSize:16, fontWeight:800, color:C.textPrimary }}>{cert.acronym || rec.cert_id.toUpperCase()}</div>
          <div style={{ fontSize:10, color:C.textMuted, marginTop:1 }}>{cert.name || ""}</div>
        </div>
        <div style={{ display:"flex", flexDirection:"column", gap:6, alignItems:"flex-end" }}>
          <div style={{ textAlign:"right" }}>
            <div style={{ fontSize:8, color:C.textMuted, textTransform:"uppercase" }}>Difficulty</div>
            <div style={{ fontSize:14, fontWeight:800, color:diffColor }}>{diff}/10</div>
            <div style={{ fontSize:8, color:diffColor }}>{rec.difficulty_label}</div>
          </div>
          <div style={{ textAlign:"right" }}>
            <div style={{ fontSize:8, color:C.textMuted, textTransform:"uppercase" }}>Market Value</div>
            <div style={{ fontSize:14, fontWeight:800, color:mvColor }}>{mv}/10</div>
          </div>
        </div>
      </div>

      {/* Score bars */}
      <div style={{ marginBottom:10 }}>
        {[["Difficulty", diff, diffColor], ["Market Value", mv, mvColor]].map(([label, val, color]) => (
          <div key={label} style={{ marginBottom:5 }}>
            <div style={{ display:"flex", justifyContent:"space-between", fontSize:9, color:C.textMuted, marginBottom:2 }}>
              <span>{label}</span><span>{val}/10</span>
            </div>
            <div style={{ height:4, background:C.bgTertiary, borderRadius:2, overflow:"hidden" }}>
              <div style={{ height:"100%", width:`${val*10}%`, background:color, borderRadius:2, transition:"width 0.6s ease" }} />
            </div>
          </div>
        ))}
      </div>

      <div style={{ fontSize:10, color:C.textSec, lineHeight:1.5, marginBottom:10 }}>
        {rec.fit_rationale}
      </div>

      {rec.gap_topics?.length > 0 && (
        <div style={{ marginBottom:10 }}>
          <div style={{ fontSize:9, color:C.rose, fontWeight:700, textTransform:"uppercase", marginBottom:4 }}>Gap Topics to Study</div>
          <div style={{ display:"flex", flexWrap:"wrap", gap:4 }}>
            {rec.gap_topics.map((t, i) => (
              <span key={i} style={{ fontSize:9, padding:"2px 7px", borderRadius:20, background:"rgba(244,63,94,0.08)", color:C.rose, border:"1px solid rgba(244,63,94,0.2)" }}>
                {t}
              </span>
            ))}
          </div>
        </div>
      )}

      {rec.known_topics?.length > 0 && (
        <div style={{ marginBottom:12 }}>
          <div style={{ fontSize:9, color:C.emerald, fontWeight:700, textTransform:"uppercase", marginBottom:4 }}>Already Know</div>
          <div style={{ display:"flex", flexWrap:"wrap", gap:4 }}>
            {rec.known_topics.map((t, i) => (
              <span key={i} style={{ fontSize:9, padding:"2px 7px", borderRadius:20, background:"rgba(16,185,129,0.08)", color:C.emerald, border:"1px solid rgba(16,185,129,0.2)" }}>
                {t}
              </span>
            ))}
          </div>
        </div>
      )}

      <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center" }}>
        <div style={{ fontSize:9, color:C.textMuted }}>
          Est. {rec.est_study_weeks} · {rec.priority?.toUpperCase()} path
        </div>
        <button onClick={(e) => toggleDomain(e.target.innerText)}
          style={{ padding:"5px 14px", borderRadius:8, border:`1px solid ${C.indigo}`, background:"rgba(99,102,241,0.1)", color:C.indigo, cursor:"pointer", fontSize:11, fontWeight:700 }}>
          Start →
        </button>
      </div>
    </div>
  );
}


// ─── Question card ──────────────────────────────────────────────────────────
function LabQuestionCard({ question: q, qNumber, total, answered, onAnswer, onNext, onPrev }) {
  const [showDistractor, setShowDistractor] = useState(false);

  const isAnswered = answered !== undefined;
  const isCorrect  = isAnswered && answered === q.correct_index;

  return (
    <div style={{ ...glass, padding:"24px 28px" }}>
      <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", marginBottom:16 }}>
        <div style={{ display:"flex", alignItems:"center", gap:10 }}>
          <span style={{ fontSize:11, fontWeight:700, color:C.textMuted }}>Q{qNumber} / {total}</span>
          <span style={{ padding:"2px 10px", borderRadius:20, fontSize:10, fontWeight:700, background:"rgba(168,85,247,0.12)", color:C.purple }}>
            {q.domain?.replace(/_/g," ")} · {q.difficulty}
          </span>
        </div>
        {isAnswered && (
          <span style={{ padding:"3px 12px", borderRadius:20, fontSize:11, fontWeight:700,
            background: isCorrect ? "rgba(16,185,129,0.12)" : "rgba(244,63,94,0.12)",
            color: isCorrect ? C.emerald : C.rose,
            border: `1px solid ${isCorrect ? C.emerald : C.rose}` }}>
            {isCorrect ? "Correct" : "Incorrect"}
          </span>
        )}
      </div>

      <p style={{ fontSize:15, color:C.textPrimary, lineHeight:1.7, margin:"0 0 20px" }}>{q.text}</p>

      <div style={{ display:"flex", flexDirection:"column", gap:8, marginBottom:20 }}>
        {(q.options || []).map((opt, j) => {
          const isSelected = answered === j;
          const isCorrectOpt = q.correct_index === j;
          const showResult = isAnswered;
          const bg = showResult
            ? (isCorrectOpt ? "rgba(16,185,129,0.12)" : (isSelected ? "rgba(244,63,94,0.1)" : "transparent"))
            : (isSelected ? "rgba(99,102,241,0.1)" : "transparent");
          const border = showResult
            ? (isCorrectOpt ? C.emerald : (isSelected ? C.rose : C.borderSub))
            : C.borderSub;
          const color = showResult
            ? (isCorrectOpt ? C.emerald : (isSelected ? C.rose : C.textSec))
            : C.textSec;
          return (
            <button key={j} onClick={(e) => toggleDomain(e.target.innerText)}
              style={{ padding:"12px 16px", borderRadius:10, border:`1px solid ${border}`,
                background:bg, color, cursor: isAnswered ? "default" : "pointer",
                textAlign:"left", fontSize:13, lineHeight:1.5, display:"flex", alignItems:"flex-start", gap:10, transition:"all 0.15s" }}>
              <span style={{ fontSize:11, fontWeight:800, flexShrink:0, marginTop:1 }}>
                {["A","B","C","D"][j]}{showResult && isCorrectOpt ? " ✓" : showResult && isSelected ? " ✗" : ""}
              </span>
              <span>{opt}</span>
            </button>
          );
        })}
      </div>

      {isAnswered && (
        <div style={{ borderTop:`1px solid ${C.borderSub}`, paddingTop:14 }}>
          {/* BEST ANSWER block — shown first for immediate reinforcement */}
          {(q.best_answer_reason || q.explanation) && (
            <div style={{ padding:"10px 12px", background:"rgba(16,185,129,0.08)", border:`1px solid rgba(16,185,129,0.25)`, borderRadius:8, marginBottom:10 }}>
              <div style={{ fontSize:10, fontWeight:700, color:C.emerald, marginBottom:4, textTransform:"uppercase", letterSpacing:"0.06em" }}>
                Best Answer
              </div>
              <p style={{ fontSize:12, color:C.textSec, lineHeight:1.65, margin:0 }}>
                {q.best_answer_reason
                  ? q.best_answer_reason.replace(/^BEST ANSWER:\s*/i, "")
                  : q.explanation}
              </p>
            </div>
          )}
          {/* WHY OTHERS ARE WRONG — collapsible */}
          {(q.why_others_wrong || q.distractor_logic) && (
            <div>
              <button onClick={(e) => toggleDomain(e.target.innerText)}
                style={{ background:"transparent", border:"none", color:C.textMuted, cursor:"pointer", fontSize:11, padding:0, marginBottom:6 }}>
                {showDistractor ? "Hide" : "Show"} Why Others Are Wrong
              </button>
              {showDistractor && (
                <p style={{ fontSize:11, color:C.textMuted, lineHeight:1.6, margin:0, padding:"8px 12px", background:C.bgTertiary, borderRadius:6 }}>
                  {q.why_others_wrong
                    ? q.why_others_wrong.replace(/^WHY OTHERS ARE WRONG:\s*/i, "")
                    : q.distractor_logic}
                </p>
              )}
            </div>
          )}
        </div>
      )}

      <div style={{ display:"flex", justifyContent:"space-between", marginTop:16 }}>
        <button onClick={(e) => toggleDomain(e.target.innerText)}>
          Previous
        </button>
        <button onClick={(e) => toggleDomain(e.target.innerText)}>
          Next
        </button>
      </div>
    </div>
  );
}

// ─── Lab Help Sidebar ──────────────────────────────────────────────────────
function LabHelpSidebar({ open, onClose }) {
  const [activeIdx, setActiveIdx] = useState(null);
  return (
    <>
      {open && <div onClick={(e) => toggleDomain(e.target.innerText)}
      <div style={{ position:"fixed", top:0, right:0, bottom:0, zIndex:195,
        width: open ? 360 : 0, overflow:"hidden", transition:"width 0.3s ease",
        background:C.bgSecondary, borderLeft:`1px solid ${C.borderSub}`, display:"flex", flexDirection:"column" }}>
        <div style={{ width:360, display:"flex", flexDirection:"column", height:"100%" }}>
          <div style={{ padding:"18px 20px 14px", borderBottom:`1px solid ${C.borderSub}`, display:"flex", justifyContent:"space-between", alignItems:"center", flexShrink:0 }}>
            <div style={{ fontSize:14, fontWeight:700, color:C.textPrimary }}>CertLab Reference</div>
            <button onClick={(e) => toggleDomain(e.target.innerText)}>×</button>
          </div>
          <div style={{ flex:1, overflowY:"auto", padding:"16px 20px" }}>
            {HELP_DEFS.map((item, i) => (
              <div key={i} style={{ marginBottom:8, borderRadius:8, border:`1px solid ${C.borderSub}`, overflow:"hidden" }}>
                <button onClick={(e) => toggleDomain(e.target.innerText)}
                  style={{ width:"100%", padding:"10px 14px", background:"transparent", border:"none", cursor:"pointer",
                    display:"flex", justifyContent:"space-between", alignItems:"center", textAlign:"left" }}>
                  <span style={{ fontSize:12, fontWeight:700, color:C.textPrimary }}>{item.term}</span>
                  <span style={{ fontSize:11, color:C.textMuted }}>{activeIdx === i ? "▲" : "▼"}</span>
                </button>
                {activeIdx === i && (
                  <div style={{ padding:"0 14px 12px", borderTop:`1px solid ${C.borderSub}` }}>
                    <p style={{ fontSize:11, color:C.textSec, lineHeight:1.65, margin:"10px 0 6px" }}>{item.def}</p>
                    <div style={{ padding:"5px 10px", borderRadius:6, background:C.bgTertiary, fontFamily:"monospace", fontSize:10, color:C.cyan }}>
                      {item.formula}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </>
  );
}
