/**
 * Dashboard v2 — Resilience-Linked Career Engine
 *
 * Gold Standard UI: dark glassmorphism matching certlab-saas-v2.html
 *   --bg-primary:   #0a0b14
 *   --bg-glass:     rgba(18,19,31,0.75)  backdrop-filter: blur(12px)
 *   --accent-indigo: #6366f1
 *   --accent-cyan:   #06b6d4
 *
 * Tabs: Jobs | Intelligence | Certs | Roadmap
 * Market toggle: US / IN in header — persisted to backend
 */
import { useEffect, useState, useCallback, useRef } from "react";
import { useRouter } from "next/router";
import axios from "axios";
import ProgressBar from "../components/progress_bar";
import TimelineCard from "../components/timeline_card";

const API = process.env.NEXT_PUBLIC_API_URL || 'https://cert-navigator-production.up.railway.app';

function authHeader() {
  const t = typeof window !== "undefined" ? localStorage.getItem("token") : null;
  return t ? { Authorization: `Bearer ${t}` } : {};
}

// ─── Gold Standard CSS vars (inline) ─────────────────────────────────────
const C = {
  bgPrimary:  "#0a0b14",
  bgSecondary:"#12131f",
  bgTertiary: "#1a1b2e",
  bgGlass:    "rgba(18,19,31,0.75)",
  bgGlassHov: "rgba(26,27,46,0.85)",
  textPrimary:"#e8e9f3",
  textSec:    "#9ca3b8",
  textMuted:  "#5f6580",
  indigo:     "#6366f1",
  cyan:       "#06b6d4",
  purple:     "#a855f7",
  amber:      "#f59e0b",
  emerald:    "#10b981",
  rose:       "#f43f5e",
  borderSub:  "rgba(99,102,241,0.12)",
  borderMed:  "rgba(99,102,241,0.25)",
  borderGlow: "rgba(99,102,241,0.5)",
  gradPrimary:"linear-gradient(135deg,#6366f1,#06b6d4)",
  gradWarm:   "linear-gradient(135deg,#f59e0b,#f43f5e)",
  gradCool:   "linear-gradient(135deg,#a855f7,#6366f1)",
  gradSuccess:"linear-gradient(135deg,#10b981,#06b6d4)",
};

const glass = {
  background:    C.bgGlass,
  backdropFilter:"blur(12px)",
  WebkitBackdropFilter:"blur(12px)",
  border:        `1px solid ${C.borderSub}`,
  borderRadius:  16,
};

// ─── Main Component ───────────────────────────────────────────────────────
export default function Dashboard() {
  const router = useRouter();

  const [user,           setUser]           = useState(null);
  const [jobs,           setJobs]           = useState([]);
  const [certRecs,       setCertRecs]       = useState(null);
  const [careerPlan,     setCareerPlan]     = useState(null);
  const [trending,       setTrending]       = useState([]);
  const [intelligence,   setIntelligence]   = useState(null);
  const [resilience,     setResilience]     = useState(null);
  const [market,         setMarket]         = useState("US");
  const [loading,        setLoading]        = useState(true);
  const [refreshing,     setRefreshing]     = useState(false);
  const [activeTab,      setActiveTab]      = useState("jobs");
  const [error,          setError]          = useState("");
  // Phase 8C: job filters
  const [filterRemote,   setFilterRemote]   = useState(false);
  const [filterLocation, setFilterLocation] = useState("");
  const [filterSalaryMin,setFilterSalaryMin]= useState("");
  const [priorityTrayOpen,setPriorityTrayOpen]= useState(true);
  const [helpOpen,       setHelpOpen]       = useState(false);
  const [chatOpen,       setChatOpen]       = useState(false);

  const fetchAll = useCallback(async (mkt = market) => {
    const headers = authHeader();
    if (!headers.Authorization) { router.push("/login"); return; }
    setLoading(true); setError("");
    try {
      const [meRes, jobsRes, certsRes, planRes, trendRes, resilienceRes] = await Promise.allSettled([
        axios.get(`${API}/users/me`,                                 { headers }),
        axios.get(`${API}/api/jobs/me?market=${mkt}${filterRemote ? "&remote=true" : ""}${filterLocation ? `&location=${encodeURIComponent(filterLocation)}` : ""}${filterSalaryMin ? `&salary_min=${filterSalaryMin}` : ""}`, { headers }),
        axios.get(`${API}/api/certs/recommendations`,                { headers }),
        axios.get(`${API}/api/career/plan`,                          { headers }),
        axios.get(`${API}/api/jobs/trending?market=${mkt}`,          { headers }),
        axios.get(`${API}/api/resilience/forecast?market=${mkt}`,    { headers }),
      ]);

      if (meRes.status       === "fulfilled") setUser(meRes.value.data);
      if (jobsRes.status     === "fulfilled") {
        const d = jobsRes.value.data;
        setJobs(d.jobs || []);
        if (d.market_intelligence) setIntelligence(d.market_intelligence);
      }
      if (certsRes.status    === "fulfilled") setCertRecs(certsRes.value.data);
      if (planRes.status     === "fulfilled") setCareerPlan(planRes.value.data);
      if (trendRes.status    === "fulfilled") setTrending(trendRes.value.data.roles || []);
      if (resilienceRes.status === "fulfilled") setResilience(resilienceRes.value.data);
      if (meRes.status === "rejected") { localStorage.removeItem("token"); router.push("/login"); }
    } catch { setError("Failed to load dashboard."); }
    finally   { setLoading(false); }
  }, [router, market]);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  const handleMarketToggle = async (mkt) => {
    setMarket(mkt);
    setRefreshing(true);
    try {
      await axios.put(`${API}/users/me/market`, { market: mkt }, { headers: authHeader() });
    } catch {}
    await fetchAll(mkt);
    setRefreshing(false);
  };

  const handleRefreshJobs = async () => {
    setRefreshing(true);
    try {
      const { data } = await axios.post(
        `${API}/api/jobs/refresh?market=${market}`, {}, { headers: authHeader() }
      );
      setJobs(data.jobs || []);
      if (data.market_intelligence) setIntelligence(data.market_intelligence);
    } catch { setError("Job refresh failed."); }
    setRefreshing(false);
  };

  const handleSignOut = () => { localStorage.removeItem("token"); router.push("/login"); };

  if (loading) return <LoadingScreen />;

  const profile = user?.profile || {};

  return (
    <div style={{ background: C.bgPrimary, minHeight: "100vh", fontFamily: "'Segoe UI',system-ui,sans-serif", color: C.textPrimary }}>
      {/* Ambient orbs */}
      <div style={{ position:"fixed", inset:0, overflow:"hidden", pointerEvents:"none", zIndex:0 }}>
        <div style={{ position:"absolute", top:"-200px", left:"-200px", width:600, height:600, borderRadius:"50%", background:"rgba(99,102,241,0.15)", filter:"blur(100px)" }} />
        <div style={{ position:"absolute", top:"40%", right:"-150px", width:500, height:500, borderRadius:"50%", background:"rgba(6,182,212,0.12)", filter:"blur(100px)" }} />
        <div style={{ position:"absolute", bottom:"-100px", left:"30%", width:400, height:400, borderRadius:"50%", background:"rgba(168,85,247,0.1)", filter:"blur(100px)" }} />
      </div>

      <div style={{ position:"relative", zIndex:1 }}>
        {/* ── Header ── */}
        <header style={{ ...glass, borderRadius:0, padding:"12px 28px", display:"flex", alignItems:"center", justifyContent:"space-between", borderBottom:`1px solid ${C.borderSub}`, position:"sticky", top:0, zIndex:100 }}>
          <div style={{ display:"flex", alignItems:"center", gap:16 }}>
            <div style={{ width:36, height:36, borderRadius:10, background:C.gradPrimary, display:"flex", alignItems:"center", justifyContent:"center", fontSize:18, fontWeight:800 }}>C</div>
            <div>
              <div style={{ fontWeight:700, fontSize:16, color:C.textPrimary }}>Career Navigator</div>
              <div style={{ fontSize:11, color:C.textMuted }}>Resilience-Linked Career Engine</div>
            </div>
          </div>

          <div style={{ display:"flex", alignItems:"center", gap:12 }}>
            {/* Market Toggle */}
            <div style={{ display:"flex", gap:4, background:C.bgTertiary, borderRadius:10, padding:4, border:`1px solid ${C.borderSub}` }}>
              {["US","IN"].map(m => (
                <button key={m} onClick={() => handleMarketToggle(m)} disabled={refreshing}
                  style={{ padding:"5px 14px", borderRadius:7, border:"none", cursor:"pointer", fontSize:12, fontWeight:700, transition:"all 0.2s",
                    background: market===m ? C.gradPrimary : "transparent",
                    color: market===m ? "#fff" : C.textSec }}>
                  {m === "US" ? "US Market" : "India Market"}
                </button>
              ))}
            </div>
            <a href="/profile" style={{ padding:"6px 14px", borderRadius:8, border:`1px solid ${C.borderSub}`, color:C.textSec, textDecoration:"none", fontSize:13 }}>
              Profile
            </a>
            <button onClick={handleSignOut} style={{ padding:"6px 14px", borderRadius:8, border:`1px solid ${C.borderMed}`, background:"transparent", color:C.rose, cursor:"pointer", fontSize:13 }}>
              Sign Out
            </button>
          </div>
        </header>

        {/* ── Stat Cards ── */}
        <div style={{ padding:"24px 28px 0", display:"grid", gridTemplateColumns:"repeat(auto-fit,minmax(180px,1fr))", gap:16 }}>
          <StatCard icon="👤" label="Current Role"   value={profile.current_role || "Set in Profile"} accent={C.indigo} />
          <StatCard icon="📊" label="Market"         value={market === "US" ? "United States" : "India"} accent={C.cyan} />
          <StatCard icon="💼" label="Jobs Matched"   value={jobs.length}                               accent={C.emerald} />
          <StatCard icon="🎓" label="Certs Held"     value={certRecs?.already_held?.length || profile.certifications?.length || 0} accent={C.amber} />
          <StatCard icon="📈" label="MPI" tooltip="Market Pressure Index: ratio of job-posting velocity to candidate density for your skill vector. Above 60 = your skills are scarce and in demand." value={profile.market_pressure_index ? `${profile.market_pressure_index}/100` : "—"} accent={C.rose} />
          <StatCard icon="🛡" label="Resilience Score" value={resilience ? `${resilience.resilience_score}/100` : "—"} accent={resilience?.disruption_signal === "Critical" ? C.rose : resilience?.disruption_signal === "High" ? C.amber : C.emerald} />
        </div>

        {error && (
          <div style={{ margin:"16px 28px 0", padding:"12px 16px", background:"rgba(244,63,94,0.1)", border:`1px solid ${C.rose}`, borderRadius:8, color:C.rose, fontSize:13 }}>
            {_errMsg(error)}
          </div>
        )}

        {/* ── Tabs ── */}
        <div style={{ padding:"20px 28px 0", display:"flex", gap:4, alignItems:"flex-end", borderBottom:`1px solid ${C.borderSub}` }}>
          {[
            { id:"jobs",        label:`Jobs (${jobs.length})` },
            { id:"intelligence",label:"Market Intelligence" },
            { id:"certs",       label:"Certifications" },
            { id:"roadmap",     label:"Disruption Roadmap" },
          ].map(tab => (
            <button key={tab.id} onClick={() => setActiveTab(tab.id)}
              style={{ padding:"8px 18px", border:"none", cursor:"pointer", fontSize:13, fontWeight:600,
                borderRadius:"8px 8px 0 0", transition:"all 0.2s",
                background: activeTab===tab.id ? C.bgGlass : "transparent",
                color: activeTab===tab.id ? C.textPrimary : C.textSec,
                borderBottom: activeTab===tab.id ? `2px solid ${C.indigo}` : "2px solid transparent" }}>
              {tab.label}
            </button>
          ))}
          <div style={{ marginLeft:"auto", display:"flex", alignItems:"center", gap:10 }}>
            {refreshing && <span style={{ fontSize:12, color:C.cyan }}>Refreshing {market} data…</span>}
            <a href="/certlab" style={{ padding:"5px 14px", borderRadius:7, border:`1px solid rgba(168,85,247,0.4)`, background:"rgba(168,85,247,0.08)", color:C.purple, textDecoration:"none", fontSize:12, fontWeight:700, whiteSpace:"nowrap" }}>
              Open CertLab
            </a>
          </div>
        </div>

        {/* ── Help Sidebar ── */}
        <HelpSidebar open={helpOpen} onClose={() => setHelpOpen(false)} profile={profile} resilience={resilience} />

        {/* ── AI Chat Widget ── */}
        <ChatWidget
          open={chatOpen}
          onToggle={() => setChatOpen(o => !o)}
          profile={profile}
          jobs={jobs}
          certRecs={certRecs}
          resilience={resilience}
          market={market}
        />

        {/* ── Floating Buttons ── */}
        <div style={{ position:"fixed", bottom:28, right:28, zIndex:200, display:"flex", flexDirection:"column", alignItems:"flex-end", gap:12 }}>
          <button onClick={() => setHelpOpen(o => !o)}
            title="Field definitions & help"
            style={{ width:44, height:44, borderRadius:"50%", background:C.gradPrimary, border:"none", cursor:"pointer",
              boxShadow:"0 4px 16px rgba(99,102,241,0.4)", fontSize:18, display:"flex", alignItems:"center",
              justifyContent:"center", color:"#fff", fontWeight:700 }}>
            ?
          </button>
          <button onClick={() => setChatOpen(o => !o)}
            title="AI Help Assistant"
            style={{ width:52, height:52, borderRadius:"50%", background:"linear-gradient(135deg,#06b6d4,#0891b2)", border:"none", cursor:"pointer",
              boxShadow:"0 4px 20px rgba(6,182,212,0.5)", fontSize:22, display:"flex", alignItems:"center",
              justifyContent:"center", color:"#fff" }}>
            💬
          </button>
        </div>

        <main style={{ padding:"24px 28px 48px" }}>

          {/* ════════ TAB: JOBS ════════ */}
          {activeTab === "jobs" && (
            <div style={{ display:"grid", gridTemplateColumns:"1fr 280px", gap:24 }}>
              <div>
                <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", marginBottom:12 }}>
                  <h2 style={{ fontSize:18, fontWeight:700, color:C.textPrimary, margin:0 }}>
                    {market === "US" ? "US" : "India"} Job Recommendations
                  </h2>
                  <button onClick={handleRefreshJobs} disabled={refreshing}
                    style={{ padding:"7px 16px", borderRadius:8, border:`1px solid ${C.borderMed}`, background:"transparent", color:C.indigo, cursor:"pointer", fontSize:13, fontWeight:600 }}>
                    Refresh
                  </button>
                </div>

                {/* Filter bar + LinkedIn/Naukri shortcuts */}
                <div style={{ display:"flex", gap:10, alignItems:"center", marginBottom:16, flexWrap:"wrap" }}>
                  <label style={{ display:"flex", alignItems:"center", gap:6, fontSize:13, color:C.textSec, cursor:"pointer" }}>
                    <input type="checkbox" checked={filterRemote} onChange={e => setFilterRemote(e.target.checked)}
                      style={{ accentColor: C.indigo }} />
                    Remote only
                  </label>
                  <input
                    type="text"
                    placeholder="Location (e.g. Chicago)"
                    value={filterLocation}
                    onChange={e => setFilterLocation(e.target.value)}
                    style={{ padding:"6px 10px", borderRadius:6, border:`1px solid ${C.borderMed}`, background:C.bgSecondary, color:C.textPrimary, fontSize:13, width:160 }}
                  />
                  <input
                    type="number"
                    placeholder="Min salary ($)"
                    value={filterSalaryMin}
                    onChange={e => setFilterSalaryMin(e.target.value)}
                    style={{ padding:"6px 10px", borderRadius:6, border:`1px solid ${C.borderMed}`, background:C.bgSecondary, color:C.textPrimary, fontSize:13, width:130 }}
                  />
                  <button onClick={() => fetchAll(market)} style={{ padding:"6px 14px", borderRadius:6, background:C.indigo, color:"#fff", border:"none", fontSize:13, fontWeight:600, cursor:"pointer" }}>
                    Apply
                  </button>
                  {(filterRemote || filterLocation || filterSalaryMin) && (
                    <button onClick={() => { setFilterRemote(false); setFilterLocation(""); setFilterSalaryMin(""); }} style={{ padding:"6px 10px", borderRadius:6, background:"transparent", color:C.textSec, border:`1px solid ${C.borderSub}`, fontSize:12, cursor:"pointer" }}>
                      Clear
                    </button>
                  )}
                  {/* LinkedIn / Naukri search shortcuts */}
                  <button
                    onClick={() => {
                      const role = encodeURIComponent(profile.target_role || profile.current_role || "IT Audit");
                      const loc  = encodeURIComponent(filterLocation || "");
                      window.open(`https://www.linkedin.com/jobs/search/?keywords=${role}&location=${loc}`, "_blank", "noopener,noreferrer");
                    }}
                    style={{ padding:"6px 14px", borderRadius:6, border:`1px solid ${C.borderMed}`, background:"transparent", color:C.textSec, fontSize:12, cursor:"pointer", fontWeight:600 }}>
                    LinkedIn
                  </button>
                  {market === "IN" && (
                    <button
                      onClick={() => {
                        const slug = (profile.target_role || profile.current_role || "it-audit").toLowerCase().replace(/\s+/g, "-");
                        window.open(`https://www.naukri.com/${slug}-jobs`, "_blank", "noopener,noreferrer");
                      }}
                      style={{ padding:"6px 14px", borderRadius:6, border:`1px solid ${C.borderMed}`, background:"transparent", color:C.textSec, fontSize:12, cursor:"pointer", fontWeight:600 }}>
                      Naukri
                    </button>
                  )}
                </div>

                {/* Resume gate */}
                {user && !user.profile_complete ? (
                  <div style={{ ...glass, padding:"32px 24px", textAlign:"center", marginBottom:16 }}>
                    <div style={{ fontSize:32, marginBottom:12 }}>📄</div>
                    <div style={{ fontSize:15, fontWeight:600, color:C.textPrimary, marginBottom:8 }}>
                      Upload your resume to unlock personalised job matches
                    </div>
                    <div style={{ fontSize:13, color:C.textSec, marginBottom:16 }}>
                      Jobs are matched to your skills, certs, and target role.
                    </div>
                    <a href="/profile" style={{ display:"inline-block", padding:"8px 24px", borderRadius:8, background:C.gradPrimary, color:"#fff", textDecoration:"none", fontSize:13, fontWeight:700 }}>
                      Go to Profile page
                    </a>
                  </div>
                ) : (
                  <>
                    {/* Priority Tray */}
                    {jobs.some(j => j.priority) && (
                      <div style={{ ...glass, marginBottom:16, overflow:"hidden", borderColor:"rgba(99,102,241,0.3)" }}>
                        <button
                          onClick={() => setPriorityTrayOpen(o => !o)}
                          style={{ width:"100%", padding:"12px 16px", background:"transparent", border:"none", cursor:"pointer",
                            display:"flex", alignItems:"center", justifyContent:"space-between" }}>
                          <div style={{ display:"flex", alignItems:"center", gap:10 }}>
                            <span style={{ padding:"2px 10px", borderRadius:20, fontSize:10, fontWeight:800, background:"rgba(99,102,241,0.2)", color:C.indigo, border:`1px solid rgba(99,102,241,0.4)` }}>
                              TOP 10 TODAY
                            </span>
                            <span style={{ fontSize:14, fontWeight:700, color:C.textPrimary }}>Priority Tray</span>
                            <span style={{ fontSize:12, color:C.textMuted }}>{jobs.filter(j => j.priority).length} roles</span>
                          </div>
                          <span style={{ fontSize:12, color:C.textMuted }}>{priorityTrayOpen ? "▲" : "▼"}</span>
                        </button>
                        {priorityTrayOpen && (
                          <div style={{ padding:"0 12px 12px" }}>
                            {jobs.filter(j => j.priority).map(j => (
                              <JobCard key={j.id} job={j} market={market} compact={true} />
                            ))}
                          </div>
                        )}
                      </div>
                    )}

                    {/* Full job list */}
                    {jobs.length === 0
                      ? <EmptyState msg="No jobs found. Try refreshing or adjusting filters." />
                      : jobs.map(j => <JobCard key={j.id} job={j} market={market} />)
                    }
                  </>
                )}
              </div>

              <div>
                <h3 style={{ fontSize:14, fontWeight:700, color:C.textPrimary, marginBottom:12, textTransform:"uppercase", letterSpacing:"0.06em" }}>
                  Trending Roles — {market}
                </h3>
                {trending.map((r,i) => <TrendCard key={i} role={r} />)}
              </div>
            </div>
          )}

          {/* ════════ TAB: INTELLIGENCE ════════ */}
          {activeTab === "intelligence" && (
            <IntelligenceTab intelligence={intelligence} market={market} profile={profile} />
          )}

          {/* ════════ TAB: CERTS ════════ */}
          {activeTab === "certs" && (
            <div>
              {user && !user.profile_complete && (
                <div style={{ ...glass, padding:"32px 24px", textAlign:"center", marginBottom:20 }}>
                  <div style={{ fontSize:32, marginBottom:12 }}>📄</div>
                  <div style={{ fontSize:15, fontWeight:600, color:C.textPrimary, marginBottom:8 }}>
                    Upload your resume to unlock personalised cert recommendations
                  </div>
                  <div style={{ fontSize:13, color:C.textSec, marginBottom:16 }}>
                    Recommendations are tailored to your skills, experience, and career goals.
                  </div>
                  <a href="/profile" style={{ display:"inline-block", padding:"8px 24px", borderRadius:8, background:C.gradPrimary, color:"#fff", textDecoration:"none", fontSize:13, fontWeight:700 }}>
                    Go to Profile page
                  </a>
                </div>
              )}
              {certRecs?.already_held?.length > 0 && (
                <div style={{ ...glass, padding:"14px 20px", marginBottom:20, display:"flex", alignItems:"center", gap:12, flexWrap:"wrap" }}>
                  <span style={{ fontSize:13, color:C.textSec }}>Certifications Held:</span>
                  {certRecs.already_held.map(id => (
                    <span key={id} style={{ padding:"3px 12px", borderRadius:20, background:`rgba(16,185,129,0.12)`, border:`1px solid ${C.emerald}`, color:C.emerald, fontSize:12, fontWeight:700 }}>
                      {id.toUpperCase()}
                    </span>
                  ))}
                </div>
              )}
              {certRecs
                ? <>
                    <CertTier title="Immediate (Next 12 Months)"   certs={certRecs.immediate}  accent={C.indigo} />
                    <CertTier title="Mid-Term (Year 2-3)"          certs={certRecs.mid_term}   accent={C.cyan} />
                    <CertTier title="Long-Term (Year 3-5)"         certs={certRecs.long_term}  accent={C.purple} />
                  </>
                : <EmptyState msg="Upload your resume to get certification recommendations." />
              }
            </div>
          )}

          {/* ════════ TAB: DISRUPTION ROADMAP ════════ */}
          {activeTab === "roadmap" && (
            <DisruptionRoadmapTab resilience={resilience} careerPlan={careerPlan} market={market} />
          )}

        </main>
      </div>
    </div>
  );
}

// ─── Market Intelligence Tab ──────────────────────────────────────────────
function IntelligenceTab({ intelligence, market, profile }) {
  if (!intelligence) return (
    <div style={{ textAlign:"center", padding:"60px 0" }}>
      <div style={{ fontSize:14, color:C.textSec }}>
        Loading market intelligence… Refresh jobs to trigger analysis.
      </div>
    </div>
  );

  const curr = market === "US" ? "USD" : "INR";

  return (
    <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:20 }}>
      {/* JD Shift Report */}
      <div style={{ ...glass, padding:"20px 24px", gridColumn:"1/-1" }}>
        <div style={{ fontSize:11, color:C.indigo, textTransform:"uppercase", letterSpacing:"0.08em", marginBottom:10, fontWeight:700 }}>
          JD Shift Report — {intelligence.snapshot_date || new Date().toISOString().slice(0,10)}
        </div>
        <p style={{ fontSize:13, color:C.textSec, lineHeight:1.7, margin:0 }}>
          {intelligence.insight || "Analyzing market signals…"}
        </p>
        {intelligence.disruption_signal && (
          <span style={{ display:"inline-block", marginTop:12, padding:"3px 12px", borderRadius:20, fontSize:11, fontWeight:700,
            background: intelligence.disruption_signal==="High Disruption" ? "rgba(244,63,94,0.12)" : intelligence.disruption_signal==="Accelerating" ? "rgba(245,158,11,0.12)" : "rgba(16,185,129,0.12)",
            color: intelligence.disruption_signal==="High Disruption" ? C.rose : intelligence.disruption_signal==="Accelerating" ? C.amber : C.emerald,
            border: `1px solid ${intelligence.disruption_signal==="High Disruption" ? C.rose : intelligence.disruption_signal==="Accelerating" ? C.amber : C.emerald}` }}>
            {intelligence.disruption_signal} — Market Velocity: {intelligence.market_velocity || "—"}/100
          </span>
        )}
      </div>

      {/* Trending Skills */}
      <div style={{ ...glass, padding:"20px 24px" }}>
        <div style={{ fontSize:13, fontWeight:700, color:C.textPrimary, marginBottom:14 }}>
          <Tooltip text="Skills whose demand_change_pct is rising in current job postings. Higher % = faster growth in employer demand for this skill. Based on keyword frequency across all fetched JDs.">
            Rising Skill Demand
          </Tooltip>
        </div>
        {(intelligence.trending_skills || []).filter(s => s && typeof s === "object").map((s,i) => (
          <div key={i} style={{ display:"flex", alignItems:"center", justifyContent:"space-between", padding:"8px 0", borderBottom:`1px solid ${C.borderSub}` }}>
            <span style={{ fontSize:13, color:C.textSec }}>{s.skill || "—"}</span>
            <span style={{ fontSize:12, fontWeight:700, color:C.emerald }}>+{s.demand_change_pct ?? 0}%</span>
          </div>
        ))}
      </div>

      {/* Declining Skills */}
      <div style={{ ...glass, padding:"20px 24px" }}>
        <div style={{ fontSize:13, fontWeight:700, color:C.textPrimary, marginBottom:14 }}>
          <Tooltip text="Skills whose demand_change_pct is negative — employers are mentioning them less in new JDs. If your resume is heavy on these, they are reducing your Hire Probability score.">
            Declining Demand
          </Tooltip>
        </div>
        {(intelligence.declining_skills || []).length === 0
          ? <div style={{ fontSize:13, color:C.textMuted }}>No declining signals in current JD corpus.</div>
          : (intelligence.declining_skills || []).filter(s => s && typeof s === "object").map((s,i) => (
            <div key={i} style={{ display:"flex", alignItems:"center", justifyContent:"space-between", padding:"8px 0", borderBottom:`1px solid ${C.borderSub}` }}>
              <span style={{ fontSize:13, color:C.textSec }}>{s.skill || "—"}</span>
              <span style={{ fontSize:12, fontWeight:700, color:C.rose }}>{s.demand_change_pct ?? 0}%</span>
            </div>
          ))
        }
      </div>

      {/* Salary Benchmark */}
      {intelligence.avg_salary_range && (
        <div style={{ ...glass, padding:"20px 24px" }}>
          <div style={{ fontSize:13, fontWeight:700, color:C.textPrimary, marginBottom:14 }}>
            <Tooltip text="Salary Velocity: real-time compensation trend for your skill vector. Min/Max are averaged across all fetched job postings with salary data. Rising average = market is paying more for your profile.">
              Salary Benchmark — {market}
            </Tooltip>
          </div>
          <div style={{ display:"flex", gap:16, flexWrap:"wrap" }}>
            {[
              ["Min", intelligence.avg_salary_range.min],
              ["Max", intelligence.avg_salary_range.max],
            ].map(([label, val]) => val ? (
              <div key={label} style={{ flex:1, minWidth:100, textAlign:"center", padding:"12px", background:C.bgTertiary, borderRadius:10 }}>
                <div style={{ fontSize:11, color:C.textMuted, marginBottom:4 }}>{label}</div>
                <div style={{ fontSize:16, fontWeight:700, color:C.indigo }}>
                  {curr === "INR"
                    ? `₹${(val/100000).toFixed(1)}L`
                    : `$${(val/1000).toFixed(0)}K`}
                </div>
              </div>
            ) : null)}
          </div>
        </div>
      )}

      {/* Top Hiring Companies */}
      {intelligence.top_hiring_companies?.length > 0 && (
        <div style={{ ...glass, padding:"20px 24px" }}>
          <div style={{ fontSize:13, fontWeight:700, color:C.textPrimary, marginBottom:14 }}>Top Hiring Companies</div>
          {(intelligence.top_hiring_companies || []).map((c,i) => (
            <div key={i} style={{ display:"flex", alignItems:"center", gap:12, padding:"8px 0", borderBottom:`1px solid ${C.borderSub}` }}>
              <div style={{ width:28, height:28, borderRadius:8, background:`rgba(99,102,241,0.12)`, display:"flex", alignItems:"center", justifyContent:"center", fontSize:11, fontWeight:700, color:C.indigo }}>{i+1}</div>
              <span style={{ fontSize:13, color:C.textSec }}>{typeof c === "object" ? c.company : c}</span>
              {typeof c === "object" && c.count > 1 && <span style={{ marginLeft:"auto", fontSize:11, color:C.textMuted }}>{c.count} openings</span>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Disruption Roadmap Tab ───────────────────────────────────────────────
function DisruptionRoadmapTab({ resilience, careerPlan, market }) {
  const [fairStep,   setFairStep]   = useState(1);
  const [fairInputs, setFairInputs] = useState({ tef: 6, vulnerability: 0.45, primary_loss: 50000, secondary_loss: 10000 });
  const [fairResult, setFairResult] = useState(null);
  const [calcLoading,setCalcLoading]= useState(false);
  const [auditFilter,setAuditFilter]= useState("all");

  const API = process.env.NEXT_PUBLIC_API_URL || 'https://cert-navigator-production.up.railway.app';

  const signalColor = {
    Critical: C.rose, High: C.amber, Moderate: C.cyan, Low: C.emerald
  };
  const trajColor = {
    declining: C.rose, augmented: C.amber, resilient: C.emerald
  };
  const trajBg = {
    declining: "rgba(244,63,94,0.1)", augmented: "rgba(245,158,11,0.1)", resilient: "rgba(16,185,129,0.1)"
  };

  const runFairCalc = async () => {
    setCalcLoading(true);
    try {
      const { data } = await axios.post(`${API}/api/resilience/fair-calc`, fairInputs);
      setFairResult(data);
      setFairStep(4);
    } catch (e) {
      // Compute locally as fallback
      const sle = fairInputs.primary_loss + fairInputs.secondary_loss;
      const ale = Math.round(fairInputs.tef * fairInputs.vulnerability * sle);
      setFairResult({
        tef: fairInputs.tef, vulnerability: fairInputs.vulnerability,
        sle, ale,
        risk_level: ale >= 500000 ? "Critical" : ale >= 200000 ? "High" : ale >= 50000 ? "Medium" : "Low",
        formula_trace: `TEF=${fairInputs.tef} × Vulnerability=${fairInputs.vulnerability} × SLE=($${fairInputs.primary_loss.toLocaleString()}+$${fairInputs.secondary_loss.toLocaleString()}) = $${ale.toLocaleString()}`,
      });
      setFairStep(4);
    }
    setCalcLoading(false);
  };

  const filteredSkills = (resilience?.skill_audit || []).filter(s =>
    auditFilter === "all" || s.trajectory === auditFilter
  );

  if (!resilience && !careerPlan) {
    return <EmptyState msg="Upload your resume to generate your Disruption Roadmap and Resilience Forecast." />;
  }

  return (
    <div>
      {/* ── Resilience Banner ── */}
      {resilience && (
        <div style={{ ...glass, padding:"20px 24px", marginBottom:20, display:"flex", gap:24, alignItems:"center", flexWrap:"wrap" }}>
          {/* Resilience Score gauge */}
          <div style={{ textAlign:"center", flexShrink:0 }}>
            <div style={{ position:"relative", width:80, height:80 }}>
              <svg width="80" height="80" viewBox="0 0 80 80">
                <circle cx="40" cy="40" r="34" fill="none" stroke={C.bgTertiary} strokeWidth="8"/>
                <circle cx="40" cy="40" r="34" fill="none"
                  stroke={signalColor[resilience.disruption_signal] || C.indigo}
                  strokeWidth="8" strokeLinecap="round"
                  strokeDasharray={`${2 * Math.PI * 34 * resilience.resilience_score / 100} ${2 * Math.PI * 34}`}
                  transform="rotate(-90 40 40)" style={{ transition:"stroke-dasharray 1s ease" }}/>
              </svg>
              <div style={{ position:"absolute", inset:0, display:"flex", alignItems:"center", justifyContent:"center", flexDirection:"column" }}>
                <div style={{ fontSize:16, fontWeight:800, color:C.textPrimary }}>{resilience.resilience_score}</div>
                <div style={{ fontSize:8, color:C.textMuted }}>/ 100</div>
              </div>
            </div>
            <div style={{ fontSize:10, color:C.textMuted, marginTop:4 }}>Resilience</div>
          </div>

          <div style={{ flex:1, minWidth:200 }}>
            <div style={{ display:"flex", alignItems:"center", gap:10, marginBottom:8 }}>
              <span style={{ fontSize:16, fontWeight:700, color:C.textPrimary }}>Disruption Signal:</span>
              <span style={{ padding:"4px 14px", borderRadius:20, fontSize:13, fontWeight:800,
                background: `${signalColor[resilience.disruption_signal]}1a`,
                color: signalColor[resilience.disruption_signal],
                border: `1px solid ${signalColor[resilience.disruption_signal]}40` }}>
                {resilience.disruption_signal}
              </span>
            </div>
            <div style={{ fontSize:13, color:C.textSec, marginBottom:10 }}>
              FAIR ALE: <span style={{ fontWeight:700, color:signalColor[resilience.disruption_signal] }}>
                {resilience.fair_model?.ale_label}
              </span> career capital at risk per year
            </div>
            {/* Skill mix bars */}
            <div style={{ display:"flex", gap:4, height:6, borderRadius:3, overflow:"hidden" }}>
              {["declining","augmented","resilient"].map(t => (
                <div key={t} style={{
                  flex: resilience.resilience_breakdown?.[`${t}_pct`] || 0,
                  background: trajColor[t], transition:"flex 0.6s ease"
                }} />
              ))}
            </div>
            <div style={{ display:"flex", gap:16, marginTop:6 }}>
              {["declining","augmented","resilient"].map(t => (
                <span key={t} style={{ fontSize:10, color:trajColor[t], fontWeight:700 }}>
                  {resilience.resilience_breakdown?.[`${t}_pct`] || 0}% {t}
                </span>
              ))}
            </div>
          </div>

          <div style={{ display:"flex", flexDirection:"column", gap:6, flexShrink:0 }}>
            {[
              ["Skill Mix",   `${resilience.resilience_breakdown?.skill_score || 0}/100`],
              ["MRV Score",   `${Math.round(resilience.mrv_score || 0)}/100`],
              ["Cert Premium",`${resilience.resilience_breakdown?.cert_premium || 0} pts`],
            ].map(([label, val]) => (
              <div key={label} style={{ display:"flex", justifyContent:"space-between", gap:20, fontSize:12 }}>
                <span style={{ color:C.textMuted }}>{label}</span>
                <span style={{ color:C.indigo, fontWeight:700 }}>{val}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:20, marginBottom:20 }}>
        {/* ── Skill Disruption Audit ── */}
        <div style={{ ...glass, padding:"20px 24px", gridColumn: resilience ? "1" : "1/-1" }}>
          <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:14 }}>
            <div style={{ fontSize:13, fontWeight:700, color:C.textPrimary }}>Skill Disruption Audit</div>
            <div style={{ display:"flex", gap:4 }}>
              {["all","declining","augmented","resilient"].map(f => (
                <button key={f} onClick={() => setAuditFilter(f)}
                  style={{ padding:"3px 10px", borderRadius:6, border:`1px solid ${auditFilter===f ? (f==="all" ? C.indigo : trajColor[f]) : C.borderSub}`,
                    background: auditFilter===f ? (f==="all" ? "rgba(99,102,241,0.12)" : trajBg[f]) : "transparent",
                    color: auditFilter===f ? (f==="all" ? C.indigo : trajColor[f]) : C.textMuted,
                    cursor:"pointer", fontSize:10, fontWeight:600, textTransform:"capitalize" }}>
                  {f}
                </button>
              ))}
            </div>
          </div>
          {(resilience?.skill_audit || []).length === 0
            ? <div style={{ fontSize:13, color:C.textMuted, textAlign:"center", padding:"24px 0" }}>Upload resume for skill audit.</div>
            : <div style={{ maxHeight:320, overflowY:"auto", display:"flex", flexDirection:"column", gap:6 }}>
                {filteredSkills.map((skill, i) => (
                  <div key={i} style={{ display:"flex", alignItems:"center", gap:10, padding:"8px 10px", borderRadius:8, background:trajBg[skill.trajectory] }}>
                    <div style={{ width:8, height:8, borderRadius:"50%", background:trajColor[skill.trajectory], flexShrink:0 }} />
                    <div style={{ flex:1, minWidth:0 }}>
                      <div style={{ fontSize:12, fontWeight:600, color:C.textPrimary, whiteSpace:"nowrap", overflow:"hidden", textOverflow:"ellipsis" }}>{skill.skill}</div>
                      <div style={{ fontSize:10, color:C.textMuted }}>{skill.timeline_to_risk}</div>
                    </div>
                    <div style={{ textAlign:"right", flexShrink:0 }}>
                      <div style={{ fontSize:12, fontWeight:800, color:trajColor[skill.trajectory] }}>{skill.automation_risk}%</div>
                      <div style={{ fontSize:9, color:C.textMuted, textTransform:"capitalize" }}>{skill.trajectory}</div>
                    </div>
                  </div>
                ))}
              </div>
          }
        </div>

        {/* ── Mitigation Plan ── */}
        {resilience?.mitigation_plan?.length > 0 && (
          <div style={{ ...glass, padding:"20px 24px" }}>
            <div style={{ fontSize:13, fontWeight:700, color:C.textPrimary, marginBottom:14 }}>Mitigation Roadmap</div>
            <div style={{ display:"flex", flexDirection:"column", gap:10, maxHeight:320, overflowY:"auto" }}>
              {resilience.mitigation_plan.map((m, i) => (
                <div key={i} style={{ padding:"10px 12px", borderRadius:8, background:C.bgTertiary, border:`1px solid ${C.borderSub}` }}>
                  <div style={{ display:"flex", justifyContent:"space-between", marginBottom:4 }}>
                    <span style={{ fontSize:10, fontWeight:700, color:C.indigo, textTransform:"uppercase" }}>{m.category}</span>
                    <span style={{ fontSize:10, fontWeight:700,
                      color: m.urgency==="Immediate" ? C.rose : m.urgency==="High" ? C.amber : C.cyan }}>
                      {m.urgency}
                    </span>
                  </div>
                  <div style={{ fontSize:12, color:C.textSec, lineHeight:1.5 }}>{m.action}</div>
                  {m.detail && <div style={{ fontSize:11, color:C.textMuted, marginTop:4, lineHeight:1.4 }}>{m.detail}</div>}
                  <div style={{ fontSize:10, color:C.textMuted, marginTop:4 }}>Timeline: {m.timeline}</div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* ── 5-Year Disruption Forecast ── */}
      {resilience?.year_forecast?.length > 0 && (
        <div style={{ ...glass, padding:"20px 24px", marginBottom:20 }}>
          <div style={{ fontSize:13, fontWeight:700, color:C.textPrimary, marginBottom:16 }}>
            5-Year Disruption Forecast
            <span style={{ fontSize:11, color:C.textMuted, marginLeft:8, fontWeight:400 }}>Action vs. Inaction scenario</span>
          </div>
          <div style={{ display:"grid", gridTemplateColumns:"repeat(5,1fr)", gap:12 }}>
            {resilience.year_forecast.map((yr) => (
              <div key={yr.year} style={{ ...glass, padding:"14px 12px", position:"relative", overflow:"hidden" }}>
                {/* MPI delta glow */}
                <div style={{ position:"absolute", top:0, right:0, width:4, bottom:0,
                  background: yr.delta_mpi >= 20 ? C.emerald : yr.delta_mpi >= 10 ? C.cyan : C.amber,
                  opacity:0.6 }} />
                <div style={{ fontSize:11, color:C.indigo, fontWeight:800, marginBottom:4 }}>{yr.year_label}</div>
                <div style={{ fontSize:10, fontWeight:700, color:C.textPrimary, marginBottom:6 }}>{yr.phase}</div>
                {yr.cert_target && (
                  <div style={{ padding:"2px 8px", borderRadius:20, background:"rgba(99,102,241,0.12)", color:C.indigo,
                    fontSize:9, fontWeight:700, display:"inline-block", marginBottom:6 }}>
                    {yr.cert_target}
                  </div>
                )}
                <div style={{ fontSize:10, color:C.textMuted, marginBottom:8, lineHeight:1.4 }}>{yr.primary_risk?.slice(0,70)}…</div>
                <div style={{ fontSize:10, marginBottom:2 }}>
                  <span style={{ color:C.emerald, fontWeight:700 }}>Action MPI: {yr.mpi_action}</span>
                </div>
                <div style={{ fontSize:10 }}>
                  <span style={{ color:C.rose, fontWeight:700 }}>Inaction MPI: {yr.mpi_inaction}</span>
                </div>
                <div style={{ marginTop:6, height:3, borderRadius:2, background:C.bgTertiary, overflow:"hidden" }}>
                  <div style={{ height:"100%", width:`${yr.resilience_action}%`, background:C.gradSuccess, borderRadius:2 }} />
                </div>
                <div style={{ fontSize:9, color:C.textMuted, marginTop:2 }}>Resilience: {yr.resilience_action}/100</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── FAIR Model Calculator ── */}
      <div style={{ ...glass, padding:"24px" }}>
        <div style={{ display:"flex", alignItems:"center", gap:10, marginBottom:20 }}>
          <div style={{ width:36, height:36, borderRadius:8, background:"rgba(245,158,11,0.15)", display:"flex", alignItems:"center", justifyContent:"center", fontSize:16 }}>⚖</div>
          <div>
            <div style={{ fontSize:14, fontWeight:700, color:C.textPrimary }}>FAIR Model Calculator</div>
            <div style={{ fontSize:11, color:C.textMuted }}>Factor Analysis of Information Risk — ALE = TEF × Vulnerability × SLE</div>
          </div>
          {fairResult && (
            <button onClick={() => { setFairStep(1); setFairResult(null); }}
              style={{ marginLeft:"auto", padding:"5px 12px", borderRadius:6, border:`1px solid ${C.borderSub}`, background:"transparent", color:C.textMuted, cursor:"pointer", fontSize:11 }}>
              Reset
            </button>
          )}
        </div>

        {/* Step progress */}
        <div style={{ display:"flex", gap:0, marginBottom:24 }}>
          {["Threat Frequency", "Vulnerability", "Loss Magnitude", "ALE Result"].map((label, i) => (
            <div key={i} style={{ flex:1, textAlign:"center" }}>
              <div style={{ display:"flex", alignItems:"center" }}>
                {i > 0 && <div style={{ flex:1, height:2, background: fairStep > i ? C.indigo : C.borderSub }} />}
                <div style={{ width:24, height:24, borderRadius:"50%", display:"flex", alignItems:"center", justifyContent:"center", fontSize:11, fontWeight:700,
                  background: fairStep > i+1 ? C.indigo : fairStep === i+1 ? "rgba(99,102,241,0.2)" : C.bgTertiary,
                  color: fairStep >= i+1 ? C.indigo : C.textMuted,
                  border: `2px solid ${fairStep >= i+1 ? C.indigo : C.borderSub}` }}>
                  {i+1}
                </div>
                {i < 3 && <div style={{ flex:1, height:2, background: fairStep > i+1 ? C.indigo : C.borderSub }} />}
              </div>
              <div style={{ fontSize:9, color: fairStep === i+1 ? C.indigo : C.textMuted, marginTop:4 }}>{label}</div>
            </div>
          ))}
        </div>

        {/* Step 1: TEF */}
        {fairStep === 1 && (
          <div>
            <div style={{ fontSize:13, color:C.textSec, marginBottom:16 }}>
              How many times per year could an automation/AI event affect your role?
              <div style={{ fontSize:11, color:C.textMuted, marginTop:4 }}>
                Examples: 6 = major AI releases/year; 12 = monthly capability updates; 24 = aggressive automation sector
              </div>
            </div>
            <div style={{ display:"flex", gap:8, marginBottom:16, flexWrap:"wrap" }}>
              {[3,6,12,24].map(v => (
                <button key={v} onClick={() => setFairInputs(p => ({...p, tef:v}))}
                  style={{ padding:"8px 16px", borderRadius:8, border:`1px solid ${fairInputs.tef===v ? C.amber : C.borderSub}`,
                    background: fairInputs.tef===v ? "rgba(245,158,11,0.12)" : "transparent",
                    color: fairInputs.tef===v ? C.amber : C.textSec, cursor:"pointer", fontSize:13, fontWeight:600 }}>
                  {v}× / year
                </button>
              ))}
              <input type="number" value={fairInputs.tef} onChange={e => setFairInputs(p => ({...p, tef:+e.target.value}))}
                style={{ width:80, padding:"8px 10px", borderRadius:8, border:`1px solid ${C.borderSub}`, background:C.bgTertiary, color:C.textPrimary, fontSize:13 }} />
            </div>
            <div style={{ marginBottom:8, fontSize:12, color:C.textMuted }}>
              Selected TEF: <span style={{ color:C.amber, fontWeight:700 }}>{fairInputs.tef} events/year</span>
            </div>
            <button onClick={() => setFairStep(2)}
              style={{ padding:"9px 24px", borderRadius:8, border:"none", background:C.gradPrimary, color:"#fff", cursor:"pointer", fontSize:13, fontWeight:700 }}>
              Next: Vulnerability →
            </button>
          </div>
        )}

        {/* Step 2: Vulnerability */}
        {fairStep === 2 && (
          <div>
            <div style={{ fontSize:13, color:C.textSec, marginBottom:16 }}>
              What fraction of your role is exposed to automation risk? (0 = fully resilient, 1 = fully automatable)
              {resilience && (
                <div style={{ marginTop:6, padding:"8px 12px", borderRadius:6, background:"rgba(99,102,241,0.08)", border:`1px solid ${C.borderSub}` }}>
                  <span style={{ fontSize:11, color:C.indigo }}>
                    Your Resilience Forecaster estimated vulnerability: <strong>{(1 - resilience.resilience_score/100).toFixed(2)}</strong>
                  </span>
                  <button onClick={() => setFairInputs(p => ({...p, vulnerability: +(1 - resilience.resilience_score/100).toFixed(2)}))}
                    style={{ marginLeft:8, padding:"2px 8px", borderRadius:4, border:`1px solid ${C.indigo}`, background:"transparent", color:C.indigo, cursor:"pointer", fontSize:10 }}>
                    Use this
                  </button>
                </div>
              )}
            </div>
            <input type="range" min="0" max="1" step="0.05" value={fairInputs.vulnerability}
              onChange={e => setFairInputs(p => ({...p, vulnerability:+e.target.value}))}
              style={{ width:"100%", marginBottom:8, accentColor:C.amber }} />
            <div style={{ display:"flex", justifyContent:"space-between", fontSize:11, color:C.textMuted, marginBottom:16 }}>
              <span>0 — Fully Resilient</span>
              <span style={{ fontWeight:800, color:C.amber }}>{(fairInputs.vulnerability * 100).toFixed(0)}% vulnerable</span>
              <span>1 — Fully Automatable</span>
            </div>
            <div style={{ display:"flex", gap:8 }}>
              <button onClick={() => setFairStep(1)}
                style={{ padding:"9px 18px", borderRadius:8, border:`1px solid ${C.borderSub}`, background:"transparent", color:C.textSec, cursor:"pointer", fontSize:13 }}>
                ← Back
              </button>
              <button onClick={() => setFairStep(3)}
                style={{ padding:"9px 24px", borderRadius:8, border:"none", background:C.gradPrimary, color:"#fff", cursor:"pointer", fontSize:13, fontWeight:700 }}>
                Next: Loss Magnitude →
              </button>
            </div>
          </div>
        )}

        {/* Step 3: Loss Magnitude */}
        {fairStep === 3 && (
          <div>
            <div style={{ fontSize:13, color:C.textSec, marginBottom:16 }}>
              Estimate the financial impact of a single automation-driven career disruption event.
            </div>
            <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:16, marginBottom:16 }}>
              {[
                ["Primary Loss", "primary_loss", "Direct: salary replacement cost, retraining, job search gap"],
                ["Secondary Loss", "secondary_loss", "Indirect: reputational loss, benefit gap, opportunity cost"],
              ].map(([label, key, desc]) => (
                <div key={key}>
                  <div style={{ fontSize:12, color:C.textSec, marginBottom:4 }}>{label}</div>
                  <div style={{ fontSize:10, color:C.textMuted, marginBottom:6 }}>{desc}</div>
                  <div style={{ display:"flex", alignItems:"center", gap:6 }}>
                    <span style={{ fontSize:13, color:C.textMuted }}>$</span>
                    <input type="number" value={fairInputs[key]} step="5000"
                      onChange={e => setFairInputs(p => ({...p, [key]:+e.target.value}))}
                      style={{ flex:1, padding:"8px 10px", borderRadius:8, border:`1px solid ${C.borderSub}`, background:C.bgTertiary, color:C.textPrimary, fontSize:13 }} />
                  </div>
                </div>
              ))}
            </div>
            <div style={{ marginBottom:16, padding:"10px 14px", borderRadius:8, background:"rgba(245,158,11,0.08)", border:`1px solid rgba(245,158,11,0.2)` }}>
              <div style={{ fontSize:12, color:C.amber }}>
                SLE = ${(fairInputs.primary_loss + fairInputs.secondary_loss).toLocaleString()} per event
              </div>
            </div>
            <div style={{ display:"flex", gap:8 }}>
              <button onClick={() => setFairStep(2)}
                style={{ padding:"9px 18px", borderRadius:8, border:`1px solid ${C.borderSub}`, background:"transparent", color:C.textSec, cursor:"pointer", fontSize:13 }}>
                ← Back
              </button>
              <button onClick={runFairCalc} disabled={calcLoading}
                style={{ padding:"9px 24px", borderRadius:8, border:"none", background:C.gradWarm, color:"#fff", cursor:"pointer", fontSize:13, fontWeight:700 }}>
                {calcLoading ? "Calculating…" : "Calculate ALE →"}
              </button>
            </div>
          </div>
        )}

        {/* Step 4: ALE Result */}
        {fairStep === 4 && fairResult && (
          <div>
            <div style={{ display:"grid", gridTemplateColumns:"repeat(4,1fr)", gap:12, marginBottom:20 }}>
              {[
                ["TEF",          fairResult.tef + " events/yr", C.indigo],
                ["Vulnerability",`${(fairResult.vulnerability*100).toFixed(0)}%`, C.amber],
                ["SLE",          `$${fairResult.sle?.toLocaleString()}`, C.purple],
                ["ALE",          `$${fairResult.ale?.toLocaleString()}`, signalColor[fairResult.risk_level] || C.rose],
              ].map(([label, val, color]) => (
                <div key={label} style={{ ...glass, padding:"14px 12px", textAlign:"center" }}>
                  <div style={{ fontSize:10, color:C.textMuted, textTransform:"uppercase", letterSpacing:"0.06em" }}>{label}</div>
                  <div style={{ fontSize:18, fontWeight:800, color, marginTop:4 }}>{val}</div>
                </div>
              ))}
            </div>
            <div style={{ padding:"16px", borderRadius:10, background:`${signalColor[fairResult.risk_level] || C.rose}12`, border:`1px solid ${signalColor[fairResult.risk_level] || C.rose}30`, marginBottom:16 }}>
              <div style={{ fontSize:13, fontWeight:700, color:signalColor[fairResult.risk_level] || C.rose, marginBottom:6 }}>
                Risk Level: {fairResult.risk_level}
              </div>
              <div style={{ fontSize:12, color:C.textSec }}>{fairResult.formula_trace}</div>
            </div>
            <div style={{ fontSize:12, color:C.textSec, lineHeight:1.7 }}>
              <strong>Interpretation:</strong> An ALE of <span style={{ color:signalColor[fairResult.risk_level], fontWeight:700 }}>${fairResult.ale?.toLocaleString()}/year</span> means
              this is your expected annualised career capital at risk from automation disruption.
              {fairResult.risk_level === "Critical" && " Immediate upskilling into AI governance and resilient roles is required."}
              {fairResult.risk_level === "High" && " Targeted cert investment (AIGP) will reduce this materially within 12 months."}
              {fairResult.risk_level === "Medium" && " Manageable with planned upskilling — schedule AIGP or AAIA within 18 months."}
              {fairResult.risk_level === "Low" && " Your profile is well-positioned. Maintain by staying current with AI governance standards."}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Study Vault Tab ──────────────────────────────────────────────────────
function StudyVaultTab({ catalog, profile }) {
  const [selectedCert,    setSelectedCert]    = useState(null);
  const [selectedType,    setSelectedType]    = useState("study_guide");
  const [selectedDomain,  setSelectedDomain]  = useState(null);
  const [generating,      setGenerating]      = useState(false);
  const [progress,        setProgress]        = useState({ pct: 0, stage: "" });
  const [artifact,        setArtifact]        = useState(null);
  const [activeQuestion,  setActiveQuestion]  = useState(0);
  const [answered,        setAnswered]        = useState({});
  const [showDistractor,  setShowDistractor]  = useState({});
  const [expandedSections,setExpandedSections]= useState({});
  const wsRef = useRef(null);

  const API = process.env.NEXT_PUBLIC_API_URL || 'https://cert-navigator-production.up.railway.app';
  const certs = catalog?.certifications || [];
  const types  = catalog?.artifact_types || [
    { id:"study_guide",   label:"Study Guide"   },
    { id:"cheat_sheet",   label:"Cheat Sheet"   },
    { id:"practice_exam", label:"Practice Exam" },
  ];

  const selectedCertObj = certs.find(c => c.id === selectedCert);

  const handleGenerate = async () => {
    if (!selectedCert || !selectedType) return;
    setGenerating(true);
    setArtifact(null);
    setAnswered({});
    setShowDistractor({});
    setExpandedSections({});
    setProgress({ pct: 5, stage: "Research Node: Loading knowledge corpus…" });

    const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
    const headers = token ? { Authorization: `Bearer ${token}` } : {};

    try {
      // First try inline generation (works without Celery)
      const { data } = await axios.post(
        `${API}/api/artifacts/generate`,
        { cert_id: selectedCert, artifact_type: selectedType || "study_guide", ...(selectedDomain ? { domain_id: selectedDomain } : {}) },
        { headers }
      );

      if (data.status === "queued" && data.ws_url) {
        // Celery is running — use WebSocket for progress
        _connectWebSocket(data.ws_url.replace("/ws/", `ws://${window.location.hostname}:8001/ws/`));
      } else if (data.status === "complete") {
        // Inline result — simulate progress stages
        setProgress({ pct: 30, stage: "Research Node: Corpus loaded…" });
        await _delay(300);
        setProgress({ pct: 60, stage: "Synthesis Node: Assembling content…" });
        await _delay(300);
        setProgress({ pct: 85, stage: "Adversarial Node: Generating questions…" });
        await _delay(300);
        setProgress({ pct: 100, stage: "Complete." });
        setArtifact(data.artifact);
        setGenerating(false);
      } else {
        throw new Error(data.error || "Generation failed");
      }
    } catch (err) {
      console.error("Artifact generation error:", err);
      setProgress({ pct: 0, stage: `Error: ${err.response?.data?.detail || err.message}` });
      setGenerating(false);
    }
  };

  const _delay = (ms) => new Promise(r => setTimeout(r, ms));

  const _connectWebSocket = (wsUrl) => {
    if (wsRef.current) wsRef.current.close();
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onmessage = (e) => {
      const msg = JSON.parse(e.data);
      setProgress({ pct: msg.progress_pct || 0, stage: msg.stage || "" });
      if (msg.state === "SUCCESS" && msg.result?.artifact) {
        setArtifact(msg.result.artifact);
        setGenerating(false);
        ws.close();
      } else if (msg.state === "FAILURE" || msg.state === "TIMEOUT") {
        setProgress({ pct: 0, stage: msg.stage || "Generation failed." });
        setGenerating(false);
        ws.close();
      }
    };
    ws.onerror = () => {
      setProgress({ pct: 0, stage: "WebSocket error — connection lost." });
      setGenerating(false);
    };
  };

  const handleAnswer = (qIdx, optIdx) => {
    if (answered[qIdx] !== undefined) return;
    setAnswered(prev => ({ ...prev, [qIdx]: optIdx }));
  };

  const toggleSection = (idx) => {
    setExpandedSections(prev => ({ ...prev, [idx]: !prev[idx] }));
  };

  const correctCount = artifact?.questions
    ? artifact.questions.filter((q, i) => answered[i] === q.correct_index).length
    : 0;
  const totalAnswered = Object.keys(answered).length;

  return (
    <div style={{ maxWidth: 900, margin: "0 auto" }}>
      {/* ── Vault Header ── */}
      <div style={{ ...glass, padding: "20px 24px", marginBottom: 20 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 16 }}>
          <div style={{ width: 40, height: 40, borderRadius: 10, background: C.gradCool, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 18 }}>📚</div>
          <div>
            <div style={{ fontSize: 16, fontWeight: 700, color: C.textPrimary }}>Study Vault</div>
            <div style={{ fontSize: 12, color: C.textMuted }}>AI-generated study materials with Distractor Logic</div>
          </div>
        </div>

        {/* Cert selector */}
        <div style={{ marginBottom: 16 }}>
          <div style={{ fontSize: 11, color: C.textMuted, textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 8 }}>Select Certification</div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
            {certs.length === 0
              ? ["AIGP", "CISA", "AAIA", "CIASP"].map(id => (
                  <button key={id} onClick={() => setSelectedCert(id.toLowerCase())}
                    style={{ padding: "8px 18px", borderRadius: 8, border: `1px solid ${selectedCert === id.toLowerCase() ? C.indigo : C.borderSub}`,
                      background: selectedCert === id.toLowerCase() ? `rgba(99,102,241,0.15)` : "transparent",
                      color: selectedCert === id.toLowerCase() ? C.indigo : C.textSec, cursor: "pointer", fontSize: 13, fontWeight: 700 }}>
                    {id}
                  </button>
                ))
              : certs.map(c => (
                  <button key={c.id} onClick={() => { setSelectedCert(c.id); setSelectedDomain(null); }}
                    style={{ padding: "8px 18px", borderRadius: 8, border: `1px solid ${selectedCert === c.id ? C.indigo : C.borderSub}`,
                      background: selectedCert === c.id ? `rgba(99,102,241,0.15)` : "transparent",
                      color: selectedCert === c.id ? C.indigo : C.textSec, cursor: "pointer", fontSize: 13, fontWeight: 700 }}>
                    {c.acronym}
                    <span style={{ fontSize: 10, color: C.textMuted, marginLeft: 4 }}>{c.demand_signal}</span>
                  </button>
                ))
            }
          </div>
        </div>

        {/* Cert info strip */}
        {selectedCertObj && (
          <div style={{ display: "flex", gap: 16, marginBottom: 16, flexWrap: "wrap" }}>
            {[
              ["Questions", selectedCertObj.exam_questions],
              ["Duration", `${selectedCertObj.duration_mins} min`],
              ["Passing", selectedCertObj.passing_score],
              ["Salary Premium", `+$${(selectedCertObj.salary_premium_usd / 1000).toFixed(0)}K`],
              ["Trend", selectedCertObj.trend],
            ].map(([label, val]) => (
              <div key={label} style={{ textAlign: "center", padding: "8px 14px", background: C.bgTertiary, borderRadius: 8 }}>
                <div style={{ fontSize: 10, color: C.textMuted }}>{label}</div>
                <div style={{ fontSize: 13, fontWeight: 700, color: C.indigo, marginTop: 2 }}>{val}</div>
              </div>
            ))}
          </div>
        )}

        {/* Domain filter (optional) */}
        {selectedCertObj?.domains?.length > 0 && (
          <div style={{ marginBottom: 16 }}>
            <div style={{ fontSize: 11, color: C.textMuted, textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 8 }}>Focus Domain (optional)</div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
              <button onClick={() => setSelectedDomain(null)}
                style={{ padding: "5px 12px", borderRadius: 6, border: `1px solid ${!selectedDomain ? C.cyan : C.borderSub}`,
                  background: !selectedDomain ? "rgba(6,182,212,0.12)" : "transparent",
                  color: !selectedDomain ? C.cyan : C.textMuted, cursor: "pointer", fontSize: 11 }}>
                All Domains
              </button>
              {selectedCertObj.domains.map(d => (
                <button key={d.id} onClick={() => setSelectedDomain(d.id)}
                  style={{ padding: "5px 12px", borderRadius: 6, border: `1px solid ${selectedDomain === d.id ? C.cyan : C.borderSub}`,
                    background: selectedDomain === d.id ? "rgba(6,182,212,0.12)" : "transparent",
                    color: selectedDomain === d.id ? C.cyan : C.textMuted, cursor: "pointer", fontSize: 11 }}>
                  {d.name} ({d.weight_pct}%)
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Artifact type selector */}
        <div style={{ display: "flex", gap: 8, marginBottom: 20 }}>
          {types.map(t => (
            <button key={t.id} onClick={() => setSelectedType(t.id)}
              style={{ flex: 1, padding: "10px 8px", borderRadius: 8, border: `1px solid ${selectedType === t.id ? C.indigo : C.borderSub}`,
                background: selectedType === t.id ? C.gradPrimary : "transparent",
                color: selectedType === t.id ? "#fff" : C.textSec, cursor: "pointer", fontSize: 12, fontWeight: 600, textAlign: "center" }}>
              {t.label || t.id.replace("_", " ")}
            </button>
          ))}
        </div>

        {/* Generate button */}
        <button
          onClick={handleGenerate}
          disabled={!selectedCert || generating}
          style={{ width: "100%", padding: "12px", borderRadius: 10, border: "none",
            background: !selectedCert || generating ? C.bgTertiary : C.gradPrimary,
            color: !selectedCert || generating ? C.textMuted : "#fff",
            cursor: !selectedCert || generating ? "not-allowed" : "pointer",
            fontSize: 14, fontWeight: 700, transition: "all 0.2s" }}>
          {generating ? "Generating…" : `Generate ${selectedType.replace(/_/g, " ").replace(/\b\w/g, l => l.toUpperCase())}`}
        </button>
      </div>

      {/* ── Progress Bar ── */}
      {generating && (
        <div style={{ ...glass, padding: "20px 24px", marginBottom: 20 }}>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
            <span style={{ fontSize: 12, color: C.textSec }}>{progress.stage}</span>
            <span style={{ fontSize: 12, fontWeight: 700, color: C.indigo }}>{progress.pct}%</span>
          </div>
          <div style={{ height: 6, background: C.bgTertiary, borderRadius: 3, overflow: "hidden" }}>
            <div style={{ height: "100%", width: `${progress.pct}%`, background: C.gradPrimary, borderRadius: 3, transition: "width 0.5s ease" }} />
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", marginTop: 10, fontSize: 10, color: C.textMuted }}>
            {["Research Node", "Synthesis Node", "Adversarial Node", "Complete"].map((stage, i) => (
              <span key={i} style={{ color: progress.pct >= (i + 1) * 25 ? C.indigo : C.textMuted, fontWeight: progress.pct >= (i + 1) * 25 ? 700 : 400 }}>
                {stage}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* ── Artifact Viewer ── */}
      {artifact && !generating && (
        <div>
          {/* Artifact header */}
          <div style={{ ...glass, padding: "16px 24px", marginBottom: 16, display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 8 }}>
            <div>
              <div style={{ fontSize: 16, fontWeight: 700, color: C.textPrimary }}>{artifact.title}</div>
              <div style={{ fontSize: 11, color: C.textMuted, marginTop: 2 }}>
                {artifact.metadata?.domains_covered?.length || 0} domains | Generated {new Date(artifact.generated_at).toLocaleTimeString()}
              </div>
            </div>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
              {artifact.fidelity_score != null && (
                <div style={{
                  padding: "4px 12px", borderRadius: 20, fontSize: 11, fontWeight: 700,
                  background: artifact.fidelity_score >= 90 ? "rgba(16,185,129,0.12)" : artifact.fidelity_score >= 75 ? "rgba(245,158,11,0.12)" : "rgba(244,63,94,0.12)",
                  color: artifact.fidelity_score >= 90 ? C.emerald : artifact.fidelity_score >= 75 ? C.amber : C.rose,
                  border: `1px solid ${artifact.fidelity_score >= 90 ? C.emerald : artifact.fidelity_score >= 75 ? C.amber : C.rose}`,
                }}>
                  Quality: {artifact.fidelity_score}/100
                </div>
              )}
              {artifact.metadata && (
                <div style={{ padding: "4px 12px", borderRadius: 20, background: "rgba(99,102,241,0.12)", color: C.indigo, fontSize: 11, fontWeight: 700 }}>
                  {artifact.cert_acronym}
                </div>
              )}
              <div style={{ padding: "4px 12px", borderRadius: 20, background: "rgba(6,182,212,0.12)", color: C.cyan, fontSize: 11, fontWeight: 700 }}>
                {artifact.type?.replace(/_/g, " ")}
              </div>
            </div>
          </div>

          {/* Study sections */}
          {artifact.sections?.length > 0 && (
            <div style={{ marginBottom: 20 }}>
              {artifact.sections.map((sec, i) => (
                <div key={i} style={{ ...glass, marginBottom: 10, overflow: "hidden" }}>
                  <button
                    onClick={() => toggleSection(i)}
                    style={{ width: "100%", padding: "14px 20px", background: "transparent", border: "none", cursor: "pointer",
                      display: "flex", justifyContent: "space-between", alignItems: "center", textAlign: "left" }}>
                    <span style={{ fontSize: 13, fontWeight: 700, color: sec.type === "overview" ? C.indigo : sec.type === "warning" || sec.type === "strategy" ? C.amber : C.textPrimary }}>
                      {sec.heading}
                    </span>
                    <span style={{ fontSize: 12, color: C.textMuted }}>{expandedSections[i] ? "▲" : "▼"}</span>
                  </button>
                  {expandedSections[i] && (
                    <div style={{ padding: "0 20px 16px", borderTop: `1px solid ${C.borderSub}` }}>
                      <pre style={{ margin: "12px 0 0", fontSize: 12, color: C.textSec, lineHeight: 1.75, whiteSpace: "pre-wrap", fontFamily: "inherit" }}>
                        {sec.content}
                      </pre>
                      {sec.type === "cheat_section" && (
                        <div style={{ marginTop: 8, display: "inline-block", padding: "2px 10px", borderRadius: 20, background: "rgba(99,102,241,0.1)", color: C.indigo, fontSize: 11 }}>
                          Weight: {sec.weight_pct}% of exam
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Practice exam questions */}
          {artifact.questions?.length > 0 && (
            <div>
              {/* Exam score banner */}
              {totalAnswered > 0 && (
                <div style={{ ...glass, padding: "14px 20px", marginBottom: 16, display: "flex", alignItems: "center", gap: 16 }}>
                  <div style={{ fontSize: 14, color: C.textSec }}>
                    Score: <span style={{ fontWeight: 700, color: correctCount / totalAnswered >= 0.7 ? C.emerald : C.rose }}>
                      {correctCount}/{totalAnswered} ({Math.round(correctCount / totalAnswered * 100)}%)
                    </span>
                  </div>
                  {totalAnswered === artifact.questions.length && (
                    <div style={{ padding: "4px 12px", borderRadius: 20, fontSize: 11, fontWeight: 700,
                      background: correctCount / totalAnswered >= 0.7 ? "rgba(16,185,129,0.12)" : "rgba(244,63,94,0.12)",
                      color: correctCount / totalAnswered >= 0.7 ? C.emerald : C.rose,
                      border: `1px solid ${correctCount / totalAnswered >= 0.7 ? C.emerald : C.rose}` }}>
                      {correctCount / totalAnswered >= 0.7 ? "Exam Ready" : "Needs Review"}
                    </div>
                  )}
                </div>
              )}

              {/* Question navigation */}
              <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 16 }}>
                {artifact.questions.map((q, i) => (
                  <button key={i} onClick={() => setActiveQuestion(i)}
                    style={{ width: 32, height: 32, borderRadius: 6, border: `1px solid ${activeQuestion === i ? C.indigo : C.borderSub}`,
                      background: answered[i] === undefined ? (activeQuestion === i ? "rgba(99,102,241,0.15)" : "transparent")
                        : answered[i] === q.correct_index ? "rgba(16,185,129,0.15)" : "rgba(244,63,94,0.15)",
                      color: answered[i] === undefined ? (activeQuestion === i ? C.indigo : C.textMuted)
                        : answered[i] === q.correct_index ? C.emerald : C.rose,
                      cursor: "pointer", fontSize: 11, fontWeight: 700 }}>
                    {i + 1}
                  </button>
                ))}
              </div>

              {/* Active question */}
              {artifact.questions[activeQuestion] && (
                <QuestionCard
                  question={artifact.questions[activeQuestion]}
                  qNumber={activeQuestion + 1}
                  totalQuestions={artifact.questions.length}
                  answered={answered[activeQuestion]}
                  showDistractor={showDistractor[activeQuestion]}
                  onAnswer={(optIdx) => handleAnswer(activeQuestion, optIdx)}
                  onToggleDistractor={() => setShowDistractor(prev => ({ ...prev, [activeQuestion]: !prev[activeQuestion] }))}
                  onNext={() => setActiveQuestion(i => Math.min(i + 1, artifact.questions.length - 1))}
                  onPrev={() => setActiveQuestion(i => Math.max(i - 1, 0))}
                />
              )}
            </div>
          )}
        </div>
      )}

      {/* Empty state */}
      {!artifact && !generating && (
        <div style={{ ...glass, padding: "48px 24px", textAlign: "center" }}>
          <div style={{ fontSize: 40, marginBottom: 12 }}>📖</div>
          <div style={{ fontSize: 15, fontWeight: 600, color: C.textPrimary, marginBottom: 8 }}>Study Vault</div>
          <div style={{ fontSize: 13, color: C.textSec }}>
            Select a certification and artifact type above, then click Generate to create your personalised study material.
          </div>
          <div style={{ display: "flex", justifyContent: "center", gap: 24, marginTop: 20 }}>
            {["Study Guide", "Cheat Sheet", "Practice Exam"].map(t => (
              <div key={t} style={{ textAlign: "center" }}>
                <div style={{ fontSize: 11, color: C.indigo, fontWeight: 700 }}>{t}</div>
                <div style={{ fontSize: 11, color: C.textMuted }}>
                  {t === "Study Guide" ? "Deep dive sections" : t === "Cheat Sheet" ? "Quick reference" : "10 MCQ + Distractors"}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function QuestionCard({ question, qNumber, totalQuestions, answered, showDistractor, onAnswer, onToggleDistractor, onNext, onPrev }) {
  const isCorrect = answered === question.correct_index;
  const isAnswered = answered !== undefined;

  return (
    <div style={{ ...glass, padding: "24px" }}>
      {/* Question header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <span style={{ padding: "2px 10px", borderRadius: 20, fontSize: 10, fontWeight: 700, background: "rgba(99,102,241,0.12)", color: C.indigo }}>
            Q{qNumber} of {totalQuestions}
          </span>
          <span style={{ padding: "2px 10px", borderRadius: 20, fontSize: 10, fontWeight: 700,
            background: question.difficulty === "hard" ? "rgba(244,63,94,0.12)" : question.difficulty === "medium" ? "rgba(245,158,11,0.12)" : "rgba(16,185,129,0.12)",
            color: question.difficulty === "hard" ? C.rose : question.difficulty === "medium" ? C.amber : C.emerald }}>
            {question.difficulty?.toUpperCase() || "MEDIUM"}
          </span>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button onClick={onPrev} disabled={qNumber === 1}
            style={{ padding: "5px 12px", borderRadius: 6, border: `1px solid ${C.borderSub}`, background: "transparent", color: C.textMuted, cursor: "pointer", fontSize: 12 }}>
            Prev
          </button>
          <button onClick={onNext} disabled={qNumber === totalQuestions}
            style={{ padding: "5px 12px", borderRadius: 6, border: `1px solid ${C.borderSub}`, background: "transparent", color: C.textMuted, cursor: "pointer", fontSize: 12 }}>
            Next
          </button>
        </div>
      </div>

      {/* Question text */}
      <p style={{ fontSize: 14, color: C.textPrimary, lineHeight: 1.75, marginBottom: 20, fontWeight: 500 }}>
        {question.text}
      </p>

      {/* Options */}
      <div style={{ display: "flex", flexDirection: "column", gap: 8, marginBottom: 16 }}>
        {question.options.map((opt, i) => {
          const isSelected = answered === i;
          const isCorrectOpt = i === question.correct_index;
          let borderColor = C.borderSub;
          let bgColor = "transparent";
          let textColor = C.textSec;

          if (isAnswered) {
            if (isCorrectOpt) { borderColor = C.emerald; bgColor = "rgba(16,185,129,0.1)"; textColor = C.emerald; }
            else if (isSelected && !isCorrectOpt) { borderColor = C.rose; bgColor = "rgba(244,63,94,0.1)"; textColor = C.rose; }
          } else if (isSelected) {
            borderColor = C.indigo; bgColor = "rgba(99,102,241,0.1)"; textColor = C.indigo;
          }

          return (
            <button key={i} onClick={() => onAnswer(i)} disabled={isAnswered}
              style={{ textAlign: "left", padding: "12px 16px", borderRadius: 8, border: `1px solid ${borderColor}`,
                background: bgColor, color: textColor, cursor: isAnswered ? "default" : "pointer",
                fontSize: 13, lineHeight: 1.5, transition: "all 0.2s", display: "flex", gap: 10, alignItems: "flex-start" }}>
              <span style={{ fontWeight: 700, flexShrink: 0, color: isAnswered && isCorrectOpt ? C.emerald : isAnswered && isSelected && !isCorrectOpt ? C.rose : C.indigo }}>
                {String.fromCharCode(65 + i)}.
              </span>
              <span>{opt}</span>
            </button>
          );
        })}
      </div>

      {/* Explanation (shown after answering) */}
      {isAnswered && (
        <div style={{ padding: "14px 16px", borderRadius: 8, background: isCorrect ? "rgba(16,185,129,0.08)" : "rgba(244,63,94,0.08)", border: `1px solid ${isCorrect ? C.emerald : C.rose}30`, marginBottom: 12 }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: isCorrect ? C.emerald : C.rose, marginBottom: 6 }}>
            {isCorrect ? "Correct" : "Incorrect"} — Explanation
          </div>
          <p style={{ fontSize: 12, color: C.textSec, lineHeight: 1.7, margin: 0 }}>
            {question.explanation}
          </p>
        </div>
      )}

      {/* Distractor Logic */}
      {isAnswered && question.distractor_logic && (
        <div>
          <button onClick={onToggleDistractor}
            style={{ fontSize: 11, color: C.indigo, background: "transparent", border: "none", cursor: "pointer", padding: "4px 0", fontWeight: 600 }}>
            {showDistractor ? "Hide" : "Show"} Distractor Logic
          </button>
          {showDistractor && (
            <div style={{ marginTop: 8, padding: "12px 14px", borderRadius: 8, background: "rgba(99,102,241,0.06)", border: `1px solid ${C.borderSub}` }}>
              <div style={{ fontSize: 11, color: C.indigo, fontWeight: 700, marginBottom: 4, textTransform: "uppercase", letterSpacing: "0.05em" }}>
                Why the wrong answers are wrong
              </div>
              <p style={{ fontSize: 12, color: C.textMuted, lineHeight: 1.7, margin: 0 }}>
                {question.distractor_logic}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Simulation Mode Tab ──────────────────────────────────────────────────
function SimulationModeTab({ profile }) {
  const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

  // Session state
  const [phase,          setPhase]          = useState("setup");   // "setup"|"question"|"results"
  const [catalog,        setCatalog]        = useState([]);
  const [selectedCert,   setSelectedCert]   = useState("aigp");
  const [selectedMode,   setSelectedMode]   = useState("practice");
  const [sessionData,    setSessionData]    = useState(null);
  const [question,       setQuestion]       = useState(null);
  const [feedback,       setFeedback]       = useState(null);     // after answering in practice
  const [results,        setResults]        = useState(null);
  const [weakness,       setWeakness]       = useState(null);
  const [loading,        setLoading]        = useState(false);
  const [error,          setError]          = useState("");
  const [elapsedSecs,    setElapsedSecs]    = useState(0);
  const timerRef = useRef(null);
  const sessionIdRef = useRef(null);

  // Load catalog on mount
  useEffect(() => {
    axios.get(`${API_URL}/api/proctor/catalog`, { headers: authHeader() })
      .then(r => setCatalog(r.data.certifications || []))
      .catch(() => {
        // fallback catalog
        setCatalog([
          { id:"aigp", acronym:"AIGP", name:"AI Governance Professional", total_questions:20, practice_q:10, exam_q:20 },
          { id:"cisa", acronym:"CISA", name:"Certified Information Systems Auditor", total_questions:15, practice_q:10, exam_q:15 },
          { id:"aaia", acronym:"AAIA", name:"AI Audit and Assurance", total_questions:10, practice_q:10, exam_q:10 },
          { id:"ciasp",acronym:"CIASP",name:"Certified Information Assurance Security Professional", total_questions:10, practice_q:10, exam_q:10 },
        ]);
      });
  }, []);

  // Load weakness report when in setup phase
  useEffect(() => {
    if (phase === "setup") {
      axios.get(`${API_URL}/api/proctor/weakness`, { headers: authHeader() })
        .then(r => setWeakness(r.data))
        .catch(() => {});
    }
  }, [phase]);

  const startTimer = () => {
    setElapsedSecs(0);
    timerRef.current = setInterval(() => setElapsedSecs(s => s + 1), 1000);
  };

  const stopTimer = () => {
    if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null; }
  };

  const formatTime = (secs) => {
    const m = Math.floor(secs / 60).toString().padStart(2, "0");
    const s = (secs % 60).toString().padStart(2, "0");
    return `${m}:${s}`;
  };

  const handleStart = async () => {
    setLoading(true); setError("");
    try {
      const { data } = await axios.post(`${API_URL}/api/proctor/session/start`,
        { cert_id: selectedCert, mode: selectedMode },
        { headers: authHeader() }
      );
      setSessionData(data);
      sessionIdRef.current = data.session_id;
      // Load first question
      const qRes = await axios.get(
        `${API_URL}/api/proctor/session/${data.session_id}/question`,
        { headers: authHeader() }
      );
      setQuestion(qRes.data);
      setFeedback(null);
      setPhase("question");
      startTimer();
    } catch (e) {
      setError(_errMsg(e?.response?.data?.detail) || "Failed to start session.");
    }
    setLoading(false);
  };

  const handleAnswer = async (optIdx) => {
    if (feedback) return;  // already answered this question
    setLoading(true);
    try {
      const sid = sessionIdRef.current;
      const { data } = await axios.post(
        `${API_URL}/api/proctor/session/${sid}/answer`,
        { answer_index: optIdx },
        { headers: authHeader() }
      );
      setFeedback({ ...data, chosen: optIdx });

      if (data.is_last) {
        stopTimer();
        // slight delay to show final feedback before transitioning
        setTimeout(async () => {
          try {
            const res = await axios.get(
              `${API_URL}/api/proctor/session/${sid}/results`,
              { headers: authHeader() }
            );
            setResults(res.data);
            setPhase("results");
          } catch { setError("Failed to load results."); }
        }, selectedMode === "practice" ? 1500 : 0);
      }
    } catch (e) {
      setError(_errMsg(e?.response?.data?.detail) || "Failed to submit answer.");
    }
    setLoading(false);
  };

  const handleNext = async () => {
    setFeedback(null);
    setLoading(true);
    try {
      const { data } = await axios.get(
        `${API_URL}/api/proctor/session/${sessionIdRef.current}/question`,
        { headers: authHeader() }
      );
      setQuestion(data);
    } catch (e) {
      setError("Failed to load next question.");
    }
    setLoading(false);
  };

  const handleReset = () => {
    stopTimer();
    setPhase("setup"); setSessionData(null); setQuestion(null);
    setFeedback(null); setResults(null); setError("");
    sessionIdRef.current = null;
  };

  const selectedCertObj = catalog.find(c => c.id === selectedCert);

  // ── SETUP PHASE ──────────────────────────────────────────────────────────
  if (phase === "setup") return (
    <div style={{ maxWidth: 860, margin: "0 auto" }}>
      {/* Header */}
      <div style={{ ...glass, padding: "20px 24px", marginBottom: 20, display: "flex", alignItems: "center", gap: 14 }}>
        <div style={{ width: 44, height: 44, borderRadius: 12, background: C.gradWarm, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 22 }}>
          🎯
        </div>
        <div>
          <div style={{ fontSize: 17, fontWeight: 700, color: C.textPrimary }}>Simulation Mode</div>
          <div style={{ fontSize: 12, color: C.textMuted }}>Adaptive proctored exam with readiness scoring and weakness tracking</div>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20, marginBottom: 20 }}>
        {/* Cert selector */}
        <div style={{ ...glass, padding: "20px 24px" }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: C.textSec, textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 14 }}>
            Select Certification
          </div>
          {catalog.map(c => (
            <div key={c.id} onClick={() => setSelectedCert(c.id)}
              style={{ display: "flex", alignItems: "center", gap: 12, padding: "10px 14px", borderRadius: 10, marginBottom: 8, cursor: "pointer", transition: "all 0.2s",
                background: selectedCert === c.id ? `rgba(99,102,241,0.12)` : C.bgTertiary,
                border: `1px solid ${selectedCert === c.id ? C.indigo : C.borderSub}` }}>
              <div style={{ width: 36, height: 36, borderRadius: 8, background: selectedCert === c.id ? C.gradPrimary : `rgba(99,102,241,0.1)`,
                display: "flex", alignItems: "center", justifyContent: "center", fontSize: 11, fontWeight: 800, color: "#fff", flexShrink: 0 }}>
                {c.acronym}
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 13, fontWeight: 600, color: selectedCert === c.id ? C.textPrimary : C.textSec }}>{c.acronym}</div>
                <div style={{ fontSize: 11, color: C.textMuted }}>{c.total_questions} questions available</div>
              </div>
              {selectedCert === c.id && (
                <div style={{ width: 8, height: 8, borderRadius: "50%", background: C.indigo, flexShrink: 0 }} />
              )}
            </div>
          ))}
        </div>

        {/* Mode selector + start */}
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <div style={{ ...glass, padding: "20px 24px" }}>
            <div style={{ fontSize: 12, fontWeight: 700, color: C.textSec, textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 14 }}>
              Exam Mode
            </div>
            {[
              { id: "practice", label: "Practice Mode", sub: `10 questions · Immediate feedback · No timer`, icon: "📝" },
              { id: "exam",     label: "Full Exam Mode", sub: `${Math.min(selectedCertObj?.exam_q || 30, selectedCertObj?.total_questions || 30)} questions · Feedback at end · 90-min timer`, icon: "🎓" },
            ].map(m => (
              <div key={m.id} onClick={() => setSelectedMode(m.id)}
                style={{ display: "flex", alignItems: "center", gap: 12, padding: "12px 14px", borderRadius: 10, marginBottom: 8, cursor: "pointer", transition: "all 0.2s",
                  background: selectedMode === m.id ? `rgba(245,158,11,0.1)` : C.bgTertiary,
                  border: `1px solid ${selectedMode === m.id ? C.amber : C.borderSub}` }}>
                <span style={{ fontSize: 20 }}>{m.icon}</span>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 13, fontWeight: 600, color: selectedMode === m.id ? C.textPrimary : C.textSec }}>{m.label}</div>
                  <div style={{ fontSize: 11, color: C.textMuted }}>{m.sub}</div>
                </div>
                {selectedMode === m.id && (
                  <div style={{ width: 8, height: 8, borderRadius: "50%", background: C.amber, flexShrink: 0 }} />
                )}
              </div>
            ))}
          </div>

          {/* Start button */}
          <button onClick={handleStart} disabled={loading}
            style={{ padding: "16px", borderRadius: 12, border: "none", cursor: loading ? "wait" : "pointer",
              background: C.gradPrimary, color: "#fff", fontSize: 15, fontWeight: 700, transition: "all 0.2s",
              opacity: loading ? 0.7 : 1, width: "100%" }}>
            {loading ? "Starting…" : `Start ${selectedMode === "exam" ? "Exam" : "Practice"} — ${selectedCertObj?.acronym || selectedCert.toUpperCase()}`}
          </button>

          {error && (
            <div style={{ padding: "10px 14px", borderRadius: 8, background: "rgba(244,63,94,0.1)", border: `1px solid ${C.rose}`, color: C.rose, fontSize: 12 }}>
              {_errMsg(error)}
            </div>
          )}
        </div>
      </div>

      {/* Weakness Report (if prior sessions) */}
      {weakness?.domains && Object.keys(weakness.domains).length > 0 && (
        <div style={{ ...glass, padding: "20px 24px" }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: C.textPrimary, marginBottom: 14 }}>
            Weakness Tracker — Across All Sessions
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))", gap: 10 }}>
            {Object.entries(weakness.domains).map(([domain, stats]) => {
              const clr = stats.status === "weak" ? C.rose : stats.status === "improving" ? C.amber : C.emerald;
              return (
                <div key={domain} style={{ padding: "12px 14px", borderRadius: 10, background: C.bgTertiary, border: `1px solid ${clr}22` }}>
                  <div style={{ fontSize: 10, color: C.textMuted, marginBottom: 4, textTransform: "uppercase", letterSpacing: "0.05em" }}>
                    {domain.replace(/_/g, " ")}
                  </div>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                    <span style={{ fontSize: 18, fontWeight: 800, color: clr }}>{stats.score_pct}%</span>
                    <span style={{ fontSize: 10, fontWeight: 700, color: clr, padding: "2px 7px", borderRadius: 10, background: `${clr}15`, border: `1px solid ${clr}30` }}>
                      {stats.status}
                    </span>
                  </div>
                  <div style={{ fontSize: 10, color: C.textMuted, marginTop: 4 }}>
                    {stats.correct}/{stats.attempts} correct
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );

  // ── QUESTION PHASE ────────────────────────────────────────────────────────
  if (phase === "question" && question) {
    const progressPct = question.total_questions > 0
      ? Math.round(((question.question_number - 1) / question.total_questions) * 100) : 0;
    const timeLeft = sessionData?.time_limit_secs
      ? Math.max(0, sessionData.time_limit_secs - elapsedSecs)
      : null;
    const timeUrgent = timeLeft !== null && timeLeft < 300;

    return (
      <div style={{ maxWidth: 780, margin: "0 auto" }}>
        {/* Progress header */}
        <div style={{ ...glass, padding: "14px 20px", marginBottom: 16, display: "flex", alignItems: "center", gap: 16 }}>
          <div style={{ flex: 1 }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 6 }}>
              <span style={{ fontSize: 12, color: C.textSec, fontWeight: 600 }}>
                Question {question.question_number} of {question.total_questions}
              </span>
              <span style={{ fontSize: 12, color: question.current_difficulty === "hard" ? C.rose : question.current_difficulty === "easy" ? C.emerald : C.amber, fontWeight: 700 }}>
                Difficulty: {question.current_difficulty}
              </span>
            </div>
            <div style={{ height: 6, borderRadius: 3, background: C.bgTertiary, overflow: "hidden" }}>
              <div style={{ height: "100%", width: `${progressPct}%`, background: C.gradPrimary, borderRadius: 3, transition: "width 0.4s ease" }} />
            </div>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 12, flexShrink: 0 }}>
            {timeLeft !== null && (
              <div style={{ fontSize: 14, fontWeight: 800, color: timeUrgent ? C.rose : C.textSec, fontFamily: "monospace", minWidth: 56 }}>
                {formatTime(timeLeft)}
              </div>
            )}
            {timeLeft === null && (
              <div style={{ fontSize: 13, color: C.textMuted, fontFamily: "monospace" }}>
                {formatTime(elapsedSecs)}
              </div>
            )}
            <button onClick={handleReset} style={{ padding: "5px 12px", borderRadius: 7, border: `1px solid ${C.borderSub}`, background: "transparent", color: C.textMuted, cursor: "pointer", fontSize: 11 }}>
              Quit
            </button>
          </div>
        </div>

        {/* Domain badge */}
        <div style={{ marginBottom: 10, display: "flex", gap: 8 }}>
          <span style={{ fontSize: 11, color: C.cyan, background: "rgba(6,182,212,0.1)", border: `1px solid rgba(6,182,212,0.2)`, padding: "3px 10px", borderRadius: 20, fontWeight: 600 }}>
            {question.domain?.replace(/_/g, " ")}
          </span>
          <span style={{ fontSize: 11, color: C.textMuted, background: C.bgTertiary, border: `1px solid ${C.borderSub}`, padding: "3px 10px", borderRadius: 20 }}>
            {selectedMode === "exam" ? "Full Exam" : "Practice"} · {(selectedCert || "").toUpperCase()}
          </span>
        </div>

        {/* Question card */}
        <div style={{ ...glass, padding: "24px 28px", marginBottom: 16 }}>
          <p style={{ fontSize: 15, color: C.textPrimary, lineHeight: 1.75, margin: 0, fontWeight: 500 }}>
            {question.text}
          </p>
        </div>

        {/* Options */}
        <div style={{ display: "flex", flexDirection: "column", gap: 10, marginBottom: 16 }}>
          {(question.options || []).map((opt, i) => {
            const isChosen   = feedback?.chosen === i;
            const isCorrect  = feedback?.correct_index === i;
            const showGreen  = feedback && isCorrect;
            const showRed    = feedback && isChosen && !feedback.correct;
            let borderClr = C.borderSub;
            let bgClr     = "transparent";
            let textClr   = C.textSec;
            if (!feedback) {
              // Hover handled via CSS — just show default
            }
            if (showGreen) { borderClr = C.emerald; bgClr = "rgba(16,185,129,0.08)"; textClr = C.emerald; }
            if (showRed)   { borderClr = C.rose;    bgClr = "rgba(244,63,94,0.08)";  textClr = C.rose; }

            return (
              <button key={i} onClick={() => handleAnswer(i)} disabled={!!feedback || loading}
                style={{ display: "flex", alignItems: "flex-start", gap: 14, padding: "14px 18px", borderRadius: 12,
                  border: `1px solid ${borderClr}`, background: bgClr,
                  cursor: feedback ? "default" : "pointer", textAlign: "left", transition: "all 0.2s", width: "100%" }}>
                <div style={{ width: 28, height: 28, borderRadius: 8, border: `1px solid ${borderClr}`, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 12, fontWeight: 800, color: textClr, flexShrink: 0, background: showGreen ? "rgba(16,185,129,0.15)" : showRed ? "rgba(244,63,94,0.15)" : C.bgTertiary }}>
                  {["A","B","C","D"][i]}
                </div>
                <span style={{ fontSize: 13, color: textClr, lineHeight: 1.55 }}>{opt}</span>
              </button>
            );
          })}
        </div>

        {/* Feedback panel (practice mode) */}
        {feedback && selectedMode === "practice" && (
          <div style={{ ...glass, padding: "18px 22px", marginBottom: 16, borderLeft: `3px solid ${feedback.correct ? C.emerald : C.rose}` }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
              <span style={{ fontSize: 18 }}>{feedback.correct ? "Correct" : "Incorrect"}</span>
              <span style={{ fontSize: 13, fontWeight: 700, color: feedback.correct ? C.emerald : C.rose }}>
                {feedback.correct ? "Well done!" : `Correct answer: ${["A","B","C","D"][feedback.correct_index]}`}
              </span>
            </div>
            {feedback.explanation && (
              <p style={{ fontSize: 13, color: C.textSec, lineHeight: 1.65, margin: "0 0 10px" }}>
                <strong style={{ color: C.textPrimary }}>Explanation:</strong> {feedback.explanation}
              </p>
            )}
            {feedback.distractor_logic && (
              <p style={{ fontSize: 12, color: C.textMuted, lineHeight: 1.6, margin: 0, borderTop: `1px solid ${C.borderSub}`, paddingTop: 10 }}>
                <strong style={{ color: C.textSec }}>Distractor Logic:</strong> {feedback.distractor_logic}
              </p>
            )}
          </div>
        )}

        {/* Exam mode: just show correct/incorrect, no explanation */}
        {feedback && selectedMode === "exam" && !feedback.is_last && (
          <div style={{ padding: "10px 16px", borderRadius: 8, background: feedback.correct ? "rgba(16,185,129,0.08)" : "rgba(244,63,94,0.08)", border: `1px solid ${feedback.correct ? C.emerald : C.rose}22`, marginBottom: 16 }}>
            <span style={{ fontSize: 13, color: feedback.correct ? C.emerald : C.rose, fontWeight: 700 }}>
              {feedback.correct ? "Correct" : "Incorrect"} — explanation available in results
            </span>
          </div>
        )}

        {/* Next button (if feedback shown and not last question) */}
        {feedback && !feedback.is_last && (
          <button onClick={handleNext} disabled={loading}
            style={{ padding: "12px 28px", borderRadius: 10, border: "none", cursor: "pointer", background: C.gradPrimary, color: "#fff", fontSize: 14, fontWeight: 700 }}>
            {loading ? "Loading…" : "Next Question"}
          </button>
        )}

        {feedback?.is_last && (
          <div style={{ fontSize: 14, color: C.textMuted, fontStyle: "italic" }}>
            Loading your results…
          </div>
        )}

        {error && (
          <div style={{ marginTop: 12, padding: "10px 14px", borderRadius: 8, background: "rgba(244,63,94,0.1)", border: `1px solid ${C.rose}`, color: C.rose, fontSize: 12 }}>
            {_errMsg(error)}
          </div>
        )}
      </div>
    );
  }

  // ── RESULTS PHASE ─────────────────────────────────────────────────────────
  if (phase === "results" && results) {
    const r = results;
    const scoreClr = r.readiness_score >= 70 ? C.emerald : r.readiness_score >= 50 ? C.amber : C.rose;
    const scoreDeg = (r.readiness_score / 100) * 220 - 110; // -110 to +110 degrees for gauge

    return (
      <div style={{ maxWidth: 860, margin: "0 auto" }}>
        {/* Results header */}
        <div style={{ ...glass, padding: "20px 24px", marginBottom: 20, display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 16 }}>
          <div>
            <div style={{ fontSize: 17, fontWeight: 700, color: C.textPrimary, marginBottom: 4 }}>
              Exam Results — {(r.cert_id || "").toUpperCase()} · {r.mode === "exam" ? "Full Exam" : "Practice"}
            </div>
            <div style={{ fontSize: 12, color: C.textMuted }}>
              {r.total_questions} questions · {Math.floor((r.elapsed_secs || 0) / 60)}m {(r.elapsed_secs || 0) % 60}s elapsed
            </div>
          </div>
          <button onClick={handleReset}
            style={{ padding: "8px 20px", borderRadius: 8, border: `1px solid ${C.borderMed}`, background: "transparent", color: C.indigo, cursor: "pointer", fontSize: 13, fontWeight: 600 }}>
            New Session
          </button>
        </div>

        {/* Score summary row */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 14, marginBottom: 20 }}>
          {[
            { label: "Raw Score",        value: `${r.raw_score_pct}%`,    clr: scoreClr },
            { label: "Correct",          value: `${r.correct_count}/${r.total_questions}`, clr: C.textPrimary },
            { label: "Readiness Score",  value: `${r.readiness_score}/100`, clr: scoreClr },
            { label: "Pass Probability", value: `${r.pass_probability_pct}%`, clr: scoreClr },
          ].map(({ label, value, clr }) => (
            <div key={label} style={{ ...glass, padding: "16px 18px", textAlign: "center" }}>
              <div style={{ fontSize: 10, color: C.textMuted, textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 6 }}>{label}</div>
              <div style={{ fontSize: 22, fontWeight: 800, color: clr }}>{value}</div>
            </div>
          ))}
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20, marginBottom: 20 }}>
          {/* Readiness gauge (SVG) */}
          <div style={{ ...glass, padding: "20px 24px", display: "flex", flexDirection: "column", alignItems: "center" }}>
            <div style={{ fontSize: 12, fontWeight: 700, color: C.textSec, textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 16 }}>
              Predicted Pass Probability
            </div>
            <svg width="180" height="110" viewBox="0 0 180 110">
              {/* Background arc */}
              <path d="M 18 100 A 72 72 0 0 1 162 100" fill="none" stroke={C.bgTertiary} strokeWidth="12" strokeLinecap="round" />
              {/* Score arc */}
              <path
                d="M 18 100 A 72 72 0 0 1 162 100"
                fill="none"
                stroke={scoreClr}
                strokeWidth="12"
                strokeLinecap="round"
                strokeDasharray={`${(r.readiness_score / 100) * 226} 226`}
              />
              {/* Score text */}
              <text x="90" y="82" textAnchor="middle" fill={scoreClr} fontSize="26" fontWeight="800">{r.readiness_score}%</text>
              <text x="90" y="100" textAnchor="middle" fill={C.textMuted} fontSize="10">pass probability</text>
              {/* Min/Max labels */}
              <text x="18" y="115" textAnchor="middle" fill={C.textMuted} fontSize="9">0%</text>
              <text x="162" y="115" textAnchor="middle" fill={C.textMuted} fontSize="9">100%</text>
            </svg>
            <div style={{ marginTop: 8, fontSize: 13, color: scoreClr, fontWeight: 700 }}>
              {r.readiness_score >= 70 ? "Exam-Ready" : r.readiness_score >= 50 ? "More Practice Needed" : "Significant Gaps — Focus on Weak Domains"}
            </div>
          </div>

          {/* Domain heatmap */}
          <div style={{ ...glass, padding: "20px 24px" }}>
            <div style={{ fontSize: 12, fontWeight: 700, color: C.textSec, textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 14 }}>
              Domain Performance
            </div>
            {Object.entries(r.domain_stats || {}).length === 0 ? (
              <div style={{ fontSize: 13, color: C.textMuted }}>No domain data yet.</div>
            ) : (
              Object.entries(r.domain_stats || {}).map(([domain, stats]) => {
                const pct = stats.score_pct || 0;
                const clr = pct >= 80 ? C.emerald : pct >= 60 ? C.amber : C.rose;
                return (
                  <div key={domain} style={{ marginBottom: 12 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                      <span style={{ fontSize: 11, color: C.textSec }}>{domain.replace(/_/g, " ")}</span>
                      <span style={{ fontSize: 11, fontWeight: 700, color: clr }}>{stats.correct}/{stats.attempts} ({pct}%)</span>
                    </div>
                    <div style={{ height: 6, borderRadius: 3, background: C.bgTertiary, overflow: "hidden" }}>
                      <div style={{ height: "100%", width: `${pct}%`, background: clr, borderRadius: 3, transition: "width 0.5s ease" }} />
                    </div>
                  </div>
                );
              })
            )}

            {/* Weakness summary */}
            {r.weakness_domains?.length > 0 && (
              <div style={{ marginTop: 14, padding: "10px 12px", borderRadius: 8, background: "rgba(244,63,94,0.06)", border: `1px solid ${C.rose}22` }}>
                <div style={{ fontSize: 11, fontWeight: 700, color: C.rose, marginBottom: 6 }}>Focus Areas</div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                  {(r.weakness_domains || []).map((d, i) => (
                    <span key={i} style={{ fontSize: 10, padding: "2px 8px", borderRadius: 10, background: "rgba(244,63,94,0.1)", border: `1px solid ${C.rose}30`, color: C.rose }}>
                      {typeof d === "string" ? d.replace(/_/g, " ") : JSON.stringify(d)}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Answer Review */}
        <div style={{ ...glass, padding: "20px 24px" }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: C.textPrimary, marginBottom: 16 }}>Answer Review</div>
          {(r.answer_review || []).map((item, i) => {
            const wasCorrect = item.correct;
            const borderClr  = wasCorrect ? C.emerald : C.rose;
            return (
              <div key={i} style={{ marginBottom: 16, padding: "14px 18px", borderRadius: 10, background: C.bgTertiary, borderLeft: `3px solid ${borderClr}` }}>
                <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 8 }}>
                  <span style={{ fontSize: 12, fontWeight: 700, color: C.textMuted }}>Q{item.question_number}</span>
                  <span style={{ fontSize: 11, padding: "2px 8px", borderRadius: 10, background: `${borderClr}18`, color: borderClr, fontWeight: 700 }}>
                    {wasCorrect ? "Correct" : "Incorrect"}
                  </span>
                  <span style={{ fontSize: 10, color: C.textMuted, marginLeft: "auto" }}>
                    {item.domain?.replace(/_/g, " ")} · {item.difficulty}
                  </span>
                </div>
                <p style={{ fontSize: 13, color: C.textSec, lineHeight: 1.6, margin: "0 0 8px" }}>{item.text}</p>
                {/* Options */}
                <div style={{ display: "flex", flexDirection: "column", gap: 4, marginBottom: 10 }}>
                  {(item.options || []).map((opt, j) => {
                    const isUserAnswer = item.user_answer_idx === j;
                    const isCorrectOpt = item.correct_index === j;
                    const optClr = isCorrectOpt ? C.emerald : (isUserAnswer && !isCorrectOpt) ? C.rose : C.textMuted;
                    return (
                      <div key={j} style={{ display: "flex", alignItems: "flex-start", gap: 8, padding: "4px 0" }}>
                        <span style={{ fontSize: 11, fontWeight: 700, color: optClr, width: 16, flexShrink: 0 }}>
                          {["A","B","C","D"][j]}{isCorrectOpt ? " ✓" : isUserAnswer ? " ✗" : ""}
                        </span>
                        <span style={{ fontSize: 12, color: optClr, lineHeight: 1.5 }}>{opt}</span>
                      </div>
                    );
                  })}
                </div>
                {/* Explanation */}
                {item.explanation && (
                  <p style={{ fontSize: 12, color: C.textSec, lineHeight: 1.6, margin: "0 0 6px", borderTop: `1px solid ${C.borderSub}`, paddingTop: 8 }}>
                    <strong style={{ color: C.textPrimary }}>Why: </strong>{item.explanation}
                  </p>
                )}
                {item.distractor_logic && (
                  <p style={{ fontSize: 11, color: C.textMuted, lineHeight: 1.55, margin: 0 }}>
                    <strong>Distractor Logic: </strong>{item.distractor_logic}
                  </p>
                )}
              </div>
            );
          })}
        </div>
      </div>
    );
  }

  // Fallback loading state
  return (
    <div style={{ textAlign: "center", padding: "60px 0" }}>
      <div style={{ fontSize: 14, color: C.textSec }}>Loading simulation…</div>
    </div>
  );
}

// ─── Sub-components ───────────────────────────────────────────────────────
function StatCard({ icon, label, value, accent, tooltip }) {
  return (
    <div style={{ ...glass, padding:"16px 20px", display:"flex", alignItems:"center", gap:14, transition:"all 0.3s" }}>
      <div style={{ width:44, height:44, borderRadius:10, background:`${accent}1a`, display:"flex", alignItems:"center", justifyContent:"center", fontSize:20, flexShrink:0 }}>
        {icon}
      </div>
      <div>
        <div style={{ fontSize:11, color:C.textMuted, textTransform:"uppercase", letterSpacing:"0.06em" }}>
          {tooltip ? <Tooltip text={tooltip}>{label}</Tooltip> : label}
        </div>
        <div style={{ fontSize:16, fontWeight:700, color:C.textPrimary, marginTop:2, lineHeight:1.2 }}>{value}</div>
      </div>
    </div>
  );
}

function JobCard({ job, market, compact }) {
  const hp        = job.hire_probability ?? job.match_score ?? 0;
  const scoreClr  = hp >= 70 ? C.emerald : hp >= 45 ? C.amber : C.rose;
  const currency  = market === "IN" ? "₹" : "$";
  const divisor   = market === "IN" ? 100000 : 1000;
  const unit      = market === "IN" ? "L" : "K";

  const handleApply = () => {
    if (job.url) {
      window.open(job.url, "_blank", "noopener,noreferrer");
    } else {
      // Deep-link to LinkedIn job search with role + company
      const kw  = encodeURIComponent(`${job.title}${job.company ? " " + job.company : ""}`);
      const loc = encodeURIComponent(job.location || "");
      window.open(
        `https://www.linkedin.com/jobs/search/?keywords=${kw}${loc ? `&location=${loc}` : ""}`,
        "_blank", "noopener,noreferrer"
      );
    }
  };

  if (compact) {
    return (
      <div style={{ ...glass, padding:"12px 16px", marginBottom:8, display:"flex", alignItems:"center", gap:12, cursor:"pointer" }}
           onClick={handleApply}>
        <div style={{ flex:1 }}>
          <div style={{ fontSize:13, fontWeight:700, color:C.textPrimary }}>{job.title}</div>
          <div style={{ fontSize:12, color:C.textSec }}>{job.company}{job.location ? ` · ${job.location}` : ""}</div>
        </div>
        <div style={{ fontSize:12, fontWeight:700, color:scoreClr, flexShrink:0 }}>{hp}% hire</div>
        <button onClick={e => { e.stopPropagation(); handleApply(); }}
          style={{ padding:"4px 12px", borderRadius:20, border:`1px solid ${C.indigo}`, background:"transparent", color:C.indigo, cursor:"pointer", fontSize:11, fontWeight:600, whiteSpace:"nowrap" }}>
          Apply Now
        </button>
      </div>
    );
  }

  return (
    <div style={{ ...glass, padding:"20px 24px", marginBottom:12, transition:"all 0.3s", cursor:"pointer",
      ...(job.priority ? { borderColor:"rgba(99,102,241,0.4)" } : {}) }}>
      <div style={{ display:"flex", justifyContent:"space-between", alignItems:"flex-start", gap:12 }}>
        <div style={{ flex:1 }}>
          <div style={{ display:"flex", alignItems:"center", gap:10, marginBottom:6, flexWrap:"wrap" }}>
            <h3 style={{ margin:0, fontSize:15, fontWeight:700, color:C.textPrimary }}>{job.title}</h3>
            {job.priority && (
              <span style={{ padding:"2px 8px", borderRadius:20, fontSize:10, fontWeight:800, background:"rgba(99,102,241,0.2)", color:C.indigo, border:`1px solid rgba(99,102,241,0.4)`, letterSpacing:"0.05em" }}>
                PRIORITY
              </span>
            )}
            {job.source && job.source !== "Mock" && (
              <span style={{ padding:"2px 8px", borderRadius:20, fontSize:10, fontWeight:700, background:`rgba(6,182,212,0.12)`, color:C.cyan, border:`1px solid rgba(6,182,212,0.25)` }}>
                {job.source}
              </span>
            )}
          </div>
          <div style={{ fontSize:13, color:C.textSec, marginBottom:8 }}>
            <span style={{ fontWeight:600 }}>{job.company}</span>
            {job.location && <span style={{ color:C.textMuted }}> · {job.location}</span>}
          </div>
          {job.salary_min && (
            <div style={{ fontSize:13, color:C.emerald, fontWeight:600, marginBottom:8 }}>
              {currency}{(job.salary_min/divisor).toFixed(0)}{unit}
              {job.salary_max && ` – ${currency}${(job.salary_max/divisor).toFixed(0)}${unit}`}
            </div>
          )}
          <p style={{ margin:0, fontSize:12, color:C.textMuted, lineHeight:1.6 }}>
            {(job.description || "").slice(0,180)}{job.description?.length > 180 ? "…" : ""}
          </p>
          {job.skills_matched?.length > 0 && (
            <div style={{ display:"flex", flexWrap:"wrap", gap:4, marginTop:10 }}>
              {job.skills_matched.slice(0,5).map((s,i) => (
                <span key={i} style={{ padding:"2px 10px", borderRadius:20, fontSize:11, background:`rgba(99,102,241,0.12)`, color:C.indigo, border:`1px solid rgba(99,102,241,0.2)` }}>
                  {s}
                </span>
              ))}
            </div>
          )}
        </div>
        {/* Hire-Probability ring */}
        <div style={{ textAlign:"center", flexShrink:0 }}>
          <div style={{ width:52, height:52, borderRadius:"50%", border:`3px solid ${scoreClr}`, display:"flex", alignItems:"center", justifyContent:"center", fontSize:14, fontWeight:800, color:scoreClr, background:`${scoreClr}12` }}>
            {hp}%
          </div>
          <div style={{ fontSize:10, color:C.textMuted, marginTop:4 }}>Hire %</div>
        </div>
      </div>
      <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", marginTop:12, paddingTop:12, borderTop:`1px solid ${C.borderSub}`, flexWrap:"wrap", gap:8 }}>
        {job.tags?.length > 0 && (
          <div style={{ display:"flex", flexWrap:"wrap", gap:4, flex:1 }}>
            {job.tags.slice(0,6).map((t,i) => (
              <span key={i} style={{ padding:"2px 9px", borderRadius:20, fontSize:11, background:C.bgTertiary, color:C.textMuted, border:`1px solid ${C.borderSub}` }}>
                {t}
              </span>
            ))}
          </div>
        )}
        <button onClick={handleApply}
          style={{ padding:"6px 16px", borderRadius:20, border:`1px solid ${C.indigo}`, background:"transparent", color:C.indigo, cursor:"pointer", fontSize:12, fontWeight:600, whiteSpace:"nowrap", flexShrink:0 }}>
          Apply Now
        </button>
      </div>
    </div>
  );
}

function TrendCard({ role }) {
  const demandClr = role.demand === "Critical" ? C.rose : role.demand === "High" ? C.amber : C.cyan;
  return (
    <div style={{ ...glass, padding:"12px 16px", marginBottom:10 }}>
      <div style={{ fontSize:13, fontWeight:600, color:C.textPrimary, marginBottom:6 }}>{role.title}</div>
      <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between" }}>
        <span style={{ fontSize:13, fontWeight:700, color:C.emerald }}>{role.growth}</span>
        <span style={{ fontSize:12, color:C.textSec }}>{role.avg_salary}</span>
      </div>
      <span style={{ display:"inline-block", marginTop:6, padding:"2px 10px", borderRadius:20, fontSize:10, fontWeight:700, background:`${demandClr}1a`, color:demandClr, border:`1px solid ${demandClr}30` }}>
        {role.demand}
      </span>
    </div>
  );
}

function CertTier({ title, certs, accent }) {
  if (!certs?.length) return null;
  return (
    <div style={{ marginBottom:24 }}>
      <div style={{ display:"flex", alignItems:"center", gap:10, marginBottom:12 }}>
        <div style={{ height:2, flex:1, background:`${accent}40` }} />
        <span style={{ fontSize:12, fontWeight:700, color:accent, textTransform:"uppercase", letterSpacing:"0.06em", whiteSpace:"nowrap" }}>{title}</span>
        <div style={{ height:2, flex:1, background:`${accent}40` }} />
      </div>
      <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fill,minmax(280px,1fr))", gap:14 }}>
        {certs.map((cert,i) => (
          <div key={i} style={{ ...glass, padding:"16px 20px" }}>
            <div style={{ display:"flex", justifyContent:"space-between", alignItems:"flex-start", marginBottom:10 }}>
              <span style={{ fontSize:15, fontWeight:800, color:accent }}>{cert.acronym || cert.name}</span>
              <span style={{ padding:"2px 10px", borderRadius:20, fontSize:11, fontWeight:700, background:`${accent}1a`, color:accent, border:`1px solid ${accent}40` }}>
                {cert.tier || "Target"}
              </span>
            </div>
            <div style={{ fontSize:12, color:C.textSec, marginBottom:8 }}>{cert.full_name || cert.name}</div>
            {cert.why && <p style={{ fontSize:12, color:C.textMuted, margin:0, lineHeight:1.6 }}>{cert.why}</p>}
            {cert.domains && (
              <div style={{ marginTop:10 }}>
                {cert.domains.slice(0,3).map((d,j) => (
                  <ProgressBar key={j} value={d.weight_pct || 0} color={accent} label={d.name || d} />
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Tooltip ──────────────────────────────────────────────────────────────
function Tooltip({ text, children }) {
  const [visible, setVisible] = useState(false);
  return (
    <span style={{ position:"relative", display:"inline-flex", alignItems:"center" }}>
      {children}
      <button
        onMouseEnter={() => setVisible(true)}
        onMouseLeave={() => setVisible(false)}
        onClick={() => setVisible(v => !v)}
        style={{ marginLeft:5, width:16, height:16, borderRadius:"50%", border:`1px solid ${C.borderMed}`,
          background:"transparent", color:C.textMuted, cursor:"pointer", fontSize:10, fontWeight:700,
          display:"inline-flex", alignItems:"center", justifyContent:"center", flexShrink:0, padding:0 }}>
        ?
      </button>
      {visible && (
        <span style={{ position:"absolute", left:0, top:"calc(100% + 6px)", zIndex:300, width:260,
          padding:"10px 14px", borderRadius:8, background:C.bgTertiary, border:`1px solid ${C.borderMed}`,
          fontSize:11, color:C.textSec, lineHeight:1.6, boxShadow:"0 8px 24px rgba(0,0,0,0.4)", pointerEvents:"none" }}>
          {text}
        </span>
      )}
    </span>
  );
}


// ─── Help Sidebar ──────────────────────────────────────────────────────────
const HELP_DEFINITIONS = [
  {
    term: "Market Pressure Index (MPI)",
    definition: "Ratio of job-posting velocity to candidate availability density for your specific skill vector. Score 0–100. Above 60 = more demand than supply — your skills are scarce. Below 40 = crowded market, differentiation required.",
    formula: "MPI = (new_postings_7d / avg_candidates) × skill_scarcity_weight",
  },
  {
    term: "Salary Velocity",
    definition: "Real-time trend of compensation for your exact skill vector across new job postings in the last 30 days. Rising = employers are paying more to attract this profile. Flat or falling = market is saturating.",
    formula: "SV = (avg_salary_this_month − avg_salary_prev_month) / avg_salary_prev_month × 100",
  },
  {
    term: "Skill ROI",
    definition: "Estimated salary delta earned per certification, based on salary premium data in active job postings vs the base rate for your role without that cert. E.g. AIGP = +$28K means job posts requiring AIGP pay $28K more on average.",
    formula: "Skill ROI = median_salary_with_cert − median_salary_without_cert",
  },
  {
    term: "Hire Probability %",
    definition: "AI-computed likelihood you would pass the initial screening for this job. Weights: Cert match (40%) + Skill overlap (30%) + Seniority fit (20%) + Market velocity (10%).",
    formula: "HP = cert_score + skill_overlap + seniority_fit + market_velocity",
  },
  {
    term: "Resilience Score",
    definition: "Probability your current role is resilient against AI automation over a 5-year horizon. Based on FAIR model: automation likelihood of your task mix, market alternatives count, and re-skilling distance to next safe role.",
    formula: "RS = (1 − automation_risk) × alternatives_density × reskill_proximity",
  },
  {
    term: "MRV (Market Readiness Value)",
    definition: "Composite score (0–100) of how market-ready your profile is right now. Combines: skill recency, cert relevance to current demand, experience seniority match, and MPI for your target role.",
    formula: "MRV = 0.35×skill_recency + 0.30×cert_relevance + 0.20×seniority + 0.15×MPI",
  },
  {
    term: "Priority Tray (Top 10 Today)",
    definition: "The 10 jobs with the highest Hire Probability % from today's full result set. These are the roles where your profile has the strongest fit — apply to these first.",
    formula: "Ranked by hire_probability DESC, top 10 flagged PRIORITY",
  },
  {
    term: "Fidelity Score (Study Vault)",
    definition: "Quality measure (0–100) of a generated study artifact. Cross-references content coverage against official domain weighting (CISA: 5 domains, AIGP: 6 domains). Agent retries generation up to 3 times until score ≥ 90.",
    formula: "Fidelity = (domains_covered / total_domains) × content_depth × question_accuracy",
  },
  {
    term: "Disruption Signal",
    definition: "Current threat level to your role from AI automation. Critical = >70% task automation risk within 3 years. High = 50–70%. Moderate = 30–50%. Low = <30%.",
    formula: "Based on FAIR model TEF × Vulnerability × Loss magnitude",
  },
];

const COMMON_QUESTIONS = [
  {
    q: "Why was a job ranked in my Top 10?",
    a: "Jobs in the Priority Tray have the highest Hire Probability %. Click any job card to see the breakdown: Cert Match, Skill Overlap, Seniority Fit, and Market Velocity scores that make up the total.",
  },
  {
    q: "How is my Skill ROI calculated?",
    a: "Skill ROI compares the median salary of job postings that require a specific cert vs those that don't, within your target role category. The difference is your estimated salary delta for earning that cert.",
  },
  {
    q: "What does a Study Vault artifact prove?",
    a: "Each artifact is generated by a 3-node AI pipeline (Research → Synthesis → Adversarial review). The Fidelity Score (Quality: X/100) tells you how completely it covers the official exam domain weightings. A score of 90+ means the material is exam-grade.",
  },
  {
    q: "How do I make my MPI go up?",
    a: "MPI rises when your skill vector matches skills in high-demand, low-supply job postings. Earning a trending cert (AIGP, CCSP) or adding a scarce skill (NIST AI RMF, Zero Trust) to your resume directly increases your MPI.",
  },
  {
    q: "Why does my wife's profile show different jobs?",
    a: "Every account is fully isolated by user ID. Her resume is parsed separately, her target role maps to a different broaden-to-narrow search query (e.g. Post-Doc → Research Scientist), and her job engine runs against research-specific sources.",
  },
];

function HelpSidebar({ open, onClose, profile, resilience }) {
  const [activeQ, setActiveQ] = useState(null);
  const [searchTerm, setSearchTerm] = useState("");

  const filtered = HELP_DEFINITIONS.filter(d =>
    !searchTerm || d.term.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <>
      {/* Backdrop */}
      {open && (
        <div onClick={onClose}
          style={{ position:"fixed", inset:0, zIndex:190, background:"rgba(0,0,0,0.4)", backdropFilter:"blur(2px)" }} />
      )}
      {/* Panel */}
      <div style={{
        position:"fixed", top:0, right:0, bottom:0, zIndex:195,
        width: open ? 380 : 0, overflow:"hidden",
        transition:"width 0.3s ease",
        background:C.bgSecondary, borderLeft:`1px solid ${C.borderSub}`,
        display:"flex", flexDirection:"column",
      }}>
        <div style={{ width:380, display:"flex", flexDirection:"column", height:"100%" }}>
          {/* Header */}
          <div style={{ padding:"20px 20px 16px", borderBottom:`1px solid ${C.borderSub}`, display:"flex", alignItems:"center", justifyContent:"space-between", flexShrink:0 }}>
            <div>
              <div style={{ fontSize:15, fontWeight:700, color:C.textPrimary }}>Field Definitions & Help</div>
              <div style={{ fontSize:11, color:C.textMuted, marginTop:2 }}>Career Intelligence Reference</div>
            </div>
            <button onClick={onClose}
              style={{ background:"transparent", border:"none", color:C.textMuted, cursor:"pointer", fontSize:18, padding:4 }}>
              ×
            </button>
          </div>

          {/* Search */}
          <div style={{ padding:"12px 20px", borderBottom:`1px solid ${C.borderSub}`, flexShrink:0 }}>
            <input
              type="text"
              placeholder="Search definitions…"
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
              style={{ width:"100%", padding:"7px 12px", borderRadius:6, border:`1px solid ${C.borderMed}`,
                background:C.bgTertiary, color:C.textPrimary, fontSize:12, boxSizing:"border-box" }}
            />
          </div>

          {/* Scrollable content */}
          <div style={{ flex:1, overflowY:"auto", padding:"16px 20px" }}>

            {/* Metric definitions */}
            <div style={{ fontSize:10, color:C.indigo, textTransform:"uppercase", letterSpacing:"0.08em", fontWeight:700, marginBottom:10 }}>
              Metric Definitions
            </div>
            {filtered.map((item, i) => (
              <div key={i} style={{ marginBottom:8, borderRadius:8, border:`1px solid ${C.borderSub}`, overflow:"hidden" }}>
                <button onClick={() => setActiveQ(activeQ === `def-${i}` ? null : `def-${i}`)}
                  style={{ width:"100%", padding:"10px 14px", background:"transparent", border:"none", cursor:"pointer",
                    display:"flex", justifyContent:"space-between", alignItems:"center", textAlign:"left" }}>
                  <span style={{ fontSize:12, fontWeight:700, color:C.textPrimary }}>{item.term}</span>
                  <span style={{ fontSize:11, color:C.textMuted, flexShrink:0, marginLeft:8 }}>{activeQ === `def-${i}` ? "▲" : "▼"}</span>
                </button>
                {activeQ === `def-${i}` && (
                  <div style={{ padding:"0 14px 12px", borderTop:`1px solid ${C.borderSub}` }}>
                    <p style={{ fontSize:11, color:C.textSec, lineHeight:1.65, margin:"10px 0 6px" }}>{item.definition}</p>
                    <div style={{ padding:"6px 10px", borderRadius:6, background:C.bgTertiary, fontFamily:"monospace", fontSize:10, color:C.cyan }}>
                      {item.formula}
                    </div>
                  </div>
                )}
              </div>
            ))}

            {/* Common questions */}
            {!searchTerm && (
              <>
                <div style={{ fontSize:10, color:C.indigo, textTransform:"uppercase", letterSpacing:"0.08em", fontWeight:700, margin:"20px 0 10px" }}>
                  Common Questions
                </div>
                {COMMON_QUESTIONS.map((item, i) => (
                  <div key={i} style={{ marginBottom:8, borderRadius:8, border:`1px solid ${C.borderSub}`, overflow:"hidden" }}>
                    <button onClick={() => setActiveQ(activeQ === `q-${i}` ? null : `q-${i}`)}
                      style={{ width:"100%", padding:"10px 14px", background:"transparent", border:"none", cursor:"pointer",
                        display:"flex", justifyContent:"space-between", alignItems:"center", textAlign:"left" }}>
                      <span style={{ fontSize:12, fontWeight:600, color:C.textSec }}>{item.q}</span>
                      <span style={{ fontSize:11, color:C.textMuted, flexShrink:0, marginLeft:8 }}>{activeQ === `q-${i}` ? "▲" : "▼"}</span>
                    </button>
                    {activeQ === `q-${i}` && (
                      <div style={{ padding:"0 14px 12px", borderTop:`1px solid ${C.borderSub}` }}>
                        <p style={{ fontSize:11, color:C.textSec, lineHeight:1.65, margin:"10px 0 0" }}>{item.a}</p>
                      </div>
                    )}
                  </div>
                ))}
              </>
            )}

            {/* Live stats from user profile */}
            {profile && Object.keys(profile).length > 0 && !searchTerm && (
              <>
                <div style={{ fontSize:10, color:C.indigo, textTransform:"uppercase", letterSpacing:"0.08em", fontWeight:700, margin:"20px 0 10px" }}>
                  Your Current Metrics
                </div>
                <div style={{ ...glass, padding:"14px 16px" }}>
                  {[
                    ["MPI",              profile.market_pressure_index ? `${profile.market_pressure_index}/100` : "—"],
                    ["MRV Score",        profile.mrv_score ? `${Math.round(profile.mrv_score)}/100` : "—"],
                    ["Experience",       profile.experience_years ? `${profile.experience_years} yrs` : "—"],
                    ["Skills detected",  profile.skills?.length || 0],
                    ["Resilience Score", resilience?.resilience_score ? `${resilience.resilience_score}/100` : "—"],
                    ["Disruption Signal",resilience?.disruption_signal || "—"],
                  ].map(([label, val]) => (
                    <div key={label} style={{ display:"flex", justifyContent:"space-between", padding:"5px 0", borderBottom:`1px solid ${C.borderSub}` }}>
                      <span style={{ fontSize:11, color:C.textMuted }}>{label}</span>
                      <span style={{ fontSize:11, fontWeight:700, color:C.textPrimary }}>{val}</span>
                    </div>
                  ))}
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </>
  );
}


function EmptyState({ msg }) {
  return (
    <div style={{ ...glass, padding:"48px 24px", textAlign:"center" }}>
      <div style={{ fontSize:32, marginBottom:12 }}>📋</div>
      <div style={{ fontSize:14, color:C.textSec }}>{msg}</div>
    </div>
  );
}

function LoadingScreen() {
  return (
    <div style={{ background:C.bgPrimary, height:"100vh", display:"flex", alignItems:"center", justifyContent:"center" }}>
      <div style={{ textAlign:"center" }}>
        <div style={{ width:40, height:40, border:`3px solid ${C.borderSub}`, borderTop:`3px solid ${C.indigo}`, borderRadius:"50%", animation:"spin 1s linear infinite", margin:"0 auto 16px" }} />
        <div style={{ fontSize:14, color:C.textSec }}>Loading Career Navigator…</div>
      </div>
    </div>
  );
}

// ─── Error string extractor — prevents "Objects are not valid as React child" ─
function _errMsg(e) {
  if (!e) return "";
  if (typeof e === "string") return e;
  if (Array.isArray(e)) return e.map(x => (typeof x === "object" ? (x?.msg || x?.message || JSON.stringify(x)) : String(x))).join("; ");
  if (typeof e === "object") return e.msg || e.message || e.detail || e.error || JSON.stringify(e);
  return String(e);
}

// ─── AI Chat Widget ────────────────────────────────────────────────────────
const CHAT_KB = [
  { q:["hire probability","hire %","hp","what is hire probability","how is hire probability calculated"],
    a:"Hire Probability (HP) is a composite score 0–100 measuring how likely you are to be shortlisted for a role. Formula: Cert Match 40% + Skill Overlap 30% + Seniority Fit 20% + Market Velocity 10%. Anything above 75% is a strong match — apply immediately." },
  { q:["mpi","market pressure","what is mpi","market pressure index"],
    a:"Market Pressure Index (MPI) 0–100 quantifies how urgently the market needs your skill set. It combines demand velocity (job posting growth), skill scarcity (supply vs demand), and certification signal strength. MPI > 70 means your profile is in active demand." },
  { q:["mrv","market readiness","mrv score"],
    a:"Market Readiness Vector (MRV) 0–100 measures how ready your resume profile is for the current market. Combines skill completeness, cert recency, experience depth, and role alignment. Aim for MRV > 80 before active job searching." },
  { q:["fidelity score","artifact quality","fidelity","quality score"],
    a:"Fidelity Score 0–100 rates how well an AI-generated study artifact meets professional certification standards. The ArtifactSovereignAgent targets Fidelity >= 90 through Research → Synthesis → Adversarial review cycles. Score >= 90 = exam-ready material." },
  { q:["disruption risk","disruption","automation risk"],
    a:"Disruption Risk % estimates the probability that AI/automation will significantly reshape or eliminate your current role within 5 years. Lower is better. IT Audit roles score ~22% disruption risk because human judgment, regulatory compliance, and ethical oversight resist automation." },
  { q:["resilience score","career resilience"],
    a:"Career Resilience Score aggregates: (1) Disruption Risk inverse, (2) Skill diversification, (3) Certification coverage, (4) Market demand trends. A resilient profile can withstand tech shifts and sector downturns. Target score > 75." },
  { q:["rising skill","trending skill","hot skill","in demand"],
    a:"Rising Skill Demand shows which competencies are growing fastest in current job postings in your market. These are calculated from weekly job posting analysis across Adzuna, Indeed, and LinkedIn. Prioritise acquiring skills with >30% YoY growth." },
  { q:["declining skill","obsolete","going away"],
    a:"Declining Demand tracks skills appearing in fewer job postings week-over-week. Skills like 'Legacy ERP' and 'Manual Testing' are declining rapidly. Pivot away from skills showing >20% YoY decline in postings." },
  { q:["salary benchmark","salary","pay","compensation"],
    a:"Salary Benchmark shows the 25th–75th percentile salary for your target role in the selected market (US or India). Data is aggregated from Adzuna and industry surveys. The range updates when you toggle between US/India markets." },
  { q:["aigp","ai governance professional"],
    a:"AIGP (AI Governance Professional) by IAPP — the fastest-growing AI cert in 2026. Covers: AI risk management, NIST AI RMF, EU AI Act, algorithmic auditing, responsible AI. Exam: ~90 questions, 150 mins. Salary premium: +$25K–35K over CISA-only. Prep time: 8–12 weeks." },
  { q:["cisa","certified information systems auditor"],
    a:"CISA by ISACA — the gold standard IT audit cert. Covers 5 domains: Auditing Process, Governance, Acquisition/Development, Operations, Protection. Exam: 150 questions, 240 mins. Passing score: 450/800. Required at most Big4 IT audit roles. Prep time: 16–20 weeks." },
  { q:["aaia","ai audit"],
    a:"AAIA (AI Audit and Assurance) by ISACA — emerging cert for auditing AI systems. Covers: AI model governance, bias auditing, explainability, EU AI Act compliance. 10 modules, 6–10 weeks prep. Pre-built interactive lab available in CertLab." },
  { q:["ciasp","information assurance"],
    a:"CIASP (Certified Information Assurance Security Professional) — covers security principles, risk frameworks, NIST 800-53, zero trust. 10 modules, 8–12 weeks prep. Pre-built interactive lab available in CertLab." },
  { q:["certlab","cert lab","lab","study vault","study guide","practice exam","cheat sheet"],
    a:"CertLab is your dedicated certification preparation workspace. Access it from the 'Open CertLab' button. It includes: AI-generated Study Guides (2–4 weeks study), Cheat Sheets (2–4 hours review), Practice Exams (10 MCQs with distractor logic), and pre-built interactive labs for AAIA and CIASP." },
  { q:["simulation","proctor","exam mode","practice mode"],
    a:"Simulation Mode in CertLab provides proctored adaptive exams. Practice Mode: 10 questions, immediate feedback per answer. Exam Mode: full question set, 90-min timer, results at end. Difficulty adapts — goes harder after 3 consecutive correct answers. Readiness score uses IRT (Item Response Theory) sigmoid." },
  { q:["priority tray","top 10","top jobs"],
    a:"The Priority Tray shows your Top 10 jobs ranked by Hire Probability today. These are the roles where your current profile has the strongest fit score. The tray is collapsible — click 'Top 10 Today' to expand/collapse." },
  { q:["apply","apply now","how to apply","apply button"],
    a:"Every job card has an 'Apply Now' button. If the job source provides a direct URL, it opens the hiring portal in a new tab. For mock/fallback jobs, it opens a targeted LinkedIn job search. For real Adzuna/Indeed jobs, it goes directly to the employer's application page." },
  { q:["resume","upload","parse"],
    a:"Upload your resume (JSON or PDF) from the Profile page. The resume parser extracts: name, role, skills, certifications, experience years. It also infers implied skills from your job title (e.g., IT Audit Manager implies SOX, ITGC, COBIT even if not listed). After upload you're redirected to this dashboard." },
  { q:["how do i upload","change my profile","update resume","profile settings"],
    a:"Go to /profile or use the Profile link in the navigation. Upload a JSON or PDF resume — the AI parser will re-run and update your domain classification, MPI, MRV, and cert recommendations automatically." },
  { q:["target role","change my target","how do i change my role"],
    a:"Your target role is inferred from your resume (current_role or target_role field). To change it, re-upload your resume or edit your JSON profile with an updated 'target_role'. The domain classifier re-runs on every upload." },
  { q:["indeed","job source","where jobs come from","adzuna","sources"],
    a:"Jobs are sourced from: Adzuna (primary, US + India), Indeed RSS (supplemental), LinkedIn RSS (supplemental), Nature Careers (research roles), Science Careers (lab/academia). When live APIs return no results, a curated mock dataset ensures you always see relevant roles." },
  { q:["gap analysis","skill gap","what should i learn"],
    a:"The Gap Analysis is built into Certifications tab — it shows which certs close your biggest skill gaps for your target role. Immediate certs (next 12 months) address the highest-priority gaps. The analysis uses Hire Probability decomposition to identify what's holding your score below 80%." },
  { q:["gcp","good clinical practice","clinical research cert"],
    a:"GCP (Good Clinical Practice, ICH E6 R2) is required for all NIH-funded research involving human subjects. Covers research ethics, IRB protocols, trial design, and FDA 21 CFR compliance. Prep time: 4–6 weeks. Salary premium: +$15K for research scientists." },
  { q:["citi","citi program","research integrity"],
    a:"CITI Program – Research Integrity & Ethics is mandatory for NIH-funded investigators. Covers responsible conduct of research, human subjects protection, and data management. Prep time: 2–4 weeks. Required at virtually all US research institutions." },
  { q:["nih grant","grant writing","r01","r21","nih-gw"],
    a:"NIH Grant Writing Fundamentals (R01/R21) — structured preparation for NIH funding mechanisms. Covers Specific Aims, Research Strategy, preliminary data framing, and budget. Reduces resubmission cycles by ~40%. Prep time: 6–10 weeks." },
  { q:["aws ml","aws machine learning","aws-mls"],
    a:"AWS Certified Machine Learning – Specialty (AWS-MLS) — most recognised cloud ML cert. Validates SageMaker, Bedrock, Feature Store, and end-to-end ML pipelines. Salary premium: +$30K. Prep time: 8–12 weeks, 65-question exam." },
  { q:["tensorflow","tf-dev","tensorflow developer"],
    a:"TensorFlow Developer Certificate validates practical deep learning: CNNs, NLP, time series. 5 practical tasks (not MCQ). Prep time: 6–8 weeks. Salary premium: +$20K. Widely recognised across AI teams at Google-ecosystem companies." },
  { q:["ckad","kubernetes","certified kubernetes"],
    a:"CKAD (Certified Kubernetes Application Developer) by CNCF — practical hands-on exam, no MCQ. Tests real kubectl skills under time pressure. Prep time: 8–10 weeks. Salary premium: +$25K. Required at cloud-native engineering roles." },
  { q:["cfa","chartered financial analyst","cfa level 1"],
    a:"CFA Level 1 — most prestigious global finance credential. 180 questions covering Ethics, Quant, FRA, Equity, Fixed Income, Portfolio Management. Prep time: 16–20 weeks. Salary premium: +$40K. Opens buy-side, sell-side, and asset management roles globally." },
  { q:["frm","financial risk manager","frm part 1"],
    a:"FRM Part 1 (GARP) — leading risk management credential. Covers risk foundations, quantitative analysis, financial markets, and valuation/risk models. 100 questions, prep time: 12–16 weeks. Salary premium: +$30K. Required at bank treasury and quant finance roles." },
  { q:["cphq","healthcare quality","certified professional healthcare"],
    a:"CPHQ (Certified Professional in Healthcare Quality) by NAHQ — gold standard for healthcare quality roles. 140-question exam covering data analytics, process improvement, patient safety, regulatory compliance. Prep time: 10–14 weeks. Salary premium: +$18K." },
  { q:["pmp","project management professional"],
    a:"PMP (Project Management Professional) by PMI — globally recognised across all industries. 180-question exam. Covers People (42%), Process (50%), Business Environment (8%). Hybrid agile/predictive approach. Salary premium: +$25K. Prep time: 12–16 weeks." },
  { q:["research lab","grant writing lab","irb simulation","what is irb simulation"],
    a:"IRB Simulation in CertLab is a practice exam focused on Institutional Review Board protocols — consent processes, vulnerable populations, risk-benefit analysis, and deviation reporting. Built specifically for research_academia domain users." },
  { q:["why do i see research jobs","why research jobs","why data science jobs","why engineering jobs","different domain"],
    a:"Career Navigator detects your professional domain from your resume — role title, skills, and education. Research scientists see research jobs and certs (GCP, CITI, NIH-GW). Data scientists see ML/AI roles. IT Audit professionals see governance roles. To change your domain, update your resume with a new target role." },
  { q:["how to generate study guide","generate artifact","how does certlab work"],
    a:"In CertLab: (1) Select your certification from the sidebar. (2) Choose artifact type — Study Guide, Cheat Sheet, or Practice Exam. (3) Optionally select a specific exam domain to focus on. (4) Click Generate. The 3-node pipeline (Research → Synthesis → Adversarial) produces exam-grade material in 20–90 seconds." },
  { q:["what is fidelity score","how is fidelity calculated"],
    a:"Fidelity Score = (domains_covered / total_domains) × content_depth_factor × question_accuracy_factor. The ArtifactSovereignAgent retries generation up to 3× until fidelity ≥ 90. Scores: 90+ = Exam Ready (green), 75–89 = Near Ready (amber), <75 = Needs Review (red)." },
  { q:["suggested labs","quick labs","one-click labs"],
    a:"Suggested Labs are pre-configured one-click generation shortcuts in CertLab. They appear at the top of the sidebar and are personalised to your domain — e.g., 'AI Governance Lab' for IT Audit, 'Research Ethics Lab' for Research & Academia. Click any to generate instantly." },
];

function _chatAnswer(input) {
  const lower = input.toLowerCase().trim();
  if (!lower) return null;
  for (const entry of CHAT_KB) {
    if (entry.q.some(kw => lower.includes(kw))) return entry.a;
  }
  // Fuzzy: any single word match from multi-word queries
  for (const entry of CHAT_KB) {
    const words = lower.split(/\s+/);
    if (words.length >= 2 && entry.q.some(kw => words.some(w => w.length > 3 && kw.includes(w)))) {
      return entry.a;
    }
  }
  return null;
}

function _dynamicAnswer(input, { profile, jobs, certRecs, resilience }) {
  const lower = input.toLowerCase().trim();

  // MPI — return real number
  if (/\bmpi\b|market pressure index|what is my mpi/.test(lower)) {
    const mpi = profile?.market_pressure_index;
    if (mpi != null) {
      const interp = mpi >= 70 ? "Your profile is in active market demand — strong signal to apply now."
                   : mpi >= 50 ? "Moderate demand. Adding one cert from your Immediate list will push MPI above 70."
                   : "Low demand signal. Focus on closing skill gaps and earning a high-priority cert first.";
      return `Your MPI is ${mpi}/100. ${interp}`;
    }
  }

  // MRV — return real number
  if (/\bmrv\b|market readiness|what is my mrv/.test(lower)) {
    const mrv = profile?.mrv_score;
    if (mrv != null) {
      const advice = mrv >= 80 ? "You're market-ready — start active applications."
                   : mrv >= 60 ? "Nearly ready. Address your top skill gap and MRV will cross 80."
                   : "Focus on skill-building and cert completion before mass applications.";
      return `Your MRV is ${mrv}/100. ${advice}`;
    }
  }

  // Certs — return top 3 immediate
  if (/what certs|which cert|certs should i|recommended cert/.test(lower)) {
    const imm = certRecs?.immediate?.slice(0, 3);
    if (imm?.length) {
      const list = imm.map(c => c.acronym || c.id?.toUpperCase()).join(", ");
      return `Your top immediate certifications are: ${list}. These address your highest-priority skill gaps for your target role. Open CertLab to generate study material for any of them.`;
    }
  }

  // Top job — return job[0]
  if (/top job|best job|my top job|first job|highest probability/.test(lower)) {
    const j = jobs?.[0];
    if (j) {
      const prob = j.hire_probability != null ? ` — Hire Probability: ${j.hire_probability}%` : "";
      return `Your top-ranked job is "${j.title}" at ${j.company} (${j.location || "Remote"})${prob}. Click Apply on the Jobs tab to open the application portal.`;
    }
  }

  // Resilience score — return real number
  if (/resilience score|my resilience|career resilience/.test(lower)) {
    const rs = resilience?.resilience_score;
    const ds = resilience?.disruption_signal;
    if (rs != null) {
      return `Your Career Resilience Score is ${rs}/100. Disruption signal: ${ds || "Moderate"}. A score above 75 means your profile can withstand significant AI-driven market shifts over the next 5 years.`;
    }
  }

  return null;
}

function ChatWidget({ open, onToggle, profile = {}, jobs = [], certRecs = null, resilience = null, market = "US" }) {
  const [msgs,    setMsgs]    = useState([
    { role:"ai", text:"Hi! I'm your Career Navigator AI assistant. Ask me about any metric, certification, or feature — or pick a quick question below." }
  ]);
  const [input,   setInput]   = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef(null);

  const hasProfile = profile && Object.keys(profile).length > 0;

  const QUICK = hasProfile ? [
    "What is my MPI?",
    "What certs should I target?",
    "Show my top job",
    "What is my resilience score?",
    "How does CertLab work?",
  ] : [
    "How is Hire Probability calculated?",
    "What is MPI?",
    "What certs should I target?",
    "How does the Apply button work?",
    "What is CertLab?",
  ];

  useEffect(() => {
    if (open && bottomRef.current) bottomRef.current.scrollIntoView({ behavior:"smooth" });
  }, [msgs, open]);

  const send = (text) => {
    if (!text.trim() || loading) return;
    const userMsg = { role:"user", text };
    setMsgs(prev => [...prev, userMsg]);
    setInput("");
    setLoading(true);
    setTimeout(() => {
      const answer =
        _dynamicAnswer(text, { profile, jobs, certRecs, resilience }) ||
        _chatAnswer(text) ||
        "I don't have a specific answer for that yet. Try asking about: Hire Probability, MPI, AIGP, CISA, CertLab, Apply buttons, Salary Benchmark, Disruption Risk, or 'What certs should I target?'";
      setMsgs(prev => [...prev, { role:"ai", text: answer }]);
      setLoading(false);
    }, 400);
  };

  if (!open) return null;

  return (
    <div style={{ position:"fixed", bottom:90, right:28, zIndex:210, width:370, maxHeight:520,
      background:"rgba(12,13,22,0.97)", border:`1px solid rgba(6,182,212,0.3)`, borderRadius:16,
      boxShadow:"0 12px 40px rgba(0,0,0,0.6)", display:"flex", flexDirection:"column", overflow:"hidden" }}>
      {/* Header */}
      <div style={{ padding:"12px 16px", background:"linear-gradient(135deg,rgba(6,182,212,0.15),rgba(99,102,241,0.15))",
        borderBottom:"1px solid rgba(6,182,212,0.2)", display:"flex", alignItems:"center", gap:10 }}>
        <div style={{ width:32, height:32, borderRadius:8, background:"linear-gradient(135deg,#06b6d4,#6366f1)",
          display:"flex", alignItems:"center", justifyContent:"center", fontSize:14 }}>AI</div>
        <div>
          <div style={{ fontSize:13, fontWeight:700, color:"#e2e8f0" }}>Career Navigator Assistant</div>
          <div style={{ fontSize:10, color:"#64748b" }}>Ask about metrics, certs, or features</div>
        </div>
        <button onClick={onToggle} style={{ marginLeft:"auto", background:"none", border:"none",
          color:"#64748b", cursor:"pointer", fontSize:18, lineHeight:1 }}>×</button>
      </div>

      {/* Messages */}
      <div style={{ flex:1, overflowY:"auto", padding:"12px 14px", display:"flex", flexDirection:"column", gap:10 }}>
        {msgs.map((m, i) => (
          <div key={i} style={{ display:"flex", justifyContent: m.role==="user" ? "flex-end" : "flex-start" }}>
            <div style={{ maxWidth:"85%", padding:"9px 13px", borderRadius: m.role==="user" ? "12px 12px 4px 12px" : "12px 12px 12px 4px",
              background: m.role==="user" ? "rgba(99,102,241,0.25)" : "rgba(255,255,255,0.06)",
              border: `1px solid ${m.role==="user" ? "rgba(99,102,241,0.4)" : "rgba(255,255,255,0.08)"}`,
              fontSize:12, color:"#cbd5e1", lineHeight:1.5 }}>
              {m.text}
            </div>
          </div>
        ))}
        {loading && (
          <div style={{ display:"flex", gap:4, padding:"8px 12px" }}>
            {[0,1,2].map(i => (
              <div key={i} style={{ width:6, height:6, borderRadius:"50%", background:"#06b6d4",
                animation:`bounce 1.2s ease-in-out ${i*0.2}s infinite` }} />
            ))}
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Quick chips */}
      <div style={{ padding:"6px 14px", display:"flex", gap:6, flexWrap:"wrap", borderTop:"1px solid rgba(255,255,255,0.05)" }}>
        {QUICK.map(q => (
          <button key={q} onClick={() => send(q)}
            style={{ padding:"3px 10px", borderRadius:20, border:"1px solid rgba(6,182,212,0.3)", background:"rgba(6,182,212,0.08)",
              color:"#06b6d4", fontSize:10, cursor:"pointer", whiteSpace:"nowrap" }}>
            {q}
          </button>
        ))}
      </div>

      {/* Input */}
      <div style={{ padding:"10px 14px", borderTop:"1px solid rgba(255,255,255,0.06)", display:"flex", gap:8 }}>
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === "Enter" && send(input)}
          placeholder="Ask anything…"
          style={{ flex:1, background:"rgba(255,255,255,0.06)", border:"1px solid rgba(255,255,255,0.1)", borderRadius:8,
            padding:"7px 10px", color:"#e2e8f0", fontSize:12, outline:"none" }}
        />
        <button onClick={() => send(input)}
          style={{ padding:"7px 14px", borderRadius:8, background:"linear-gradient(135deg,#06b6d4,#0891b2)",
            border:"none", color:"#fff", cursor:"pointer", fontSize:12, fontWeight:700 }}>
          Send
        </button>
      </div>
      <style>{`@keyframes bounce{0%,80%,100%{transform:scale(0)}40%{transform:scale(1)}}`}</style>
    </div>
  );
}
