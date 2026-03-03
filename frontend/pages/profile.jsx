/**
 * Profile Page — Phase 1
 * Displays the authenticated user's parsed resume data:
 *   - Name, current role, location, experience
 *   - Skills with progress bars
 *   - Certifications with status badges
 *   - Career target role
 *   - Resume upload button (JSON or PDF)
 */
import { useEffect, useState } from "react";
import { useRouter } from "next/router";
import axios from "axios";
import ProgressBar from "../components/progress_bar";

const API = process.env.NEXT_PUBLIC_API_URL || 'https://cert-navigator-production.up.railway.app';

export default function Profile() {
  const router = useRouter();
  const [user,       setUser]       = useState(null);
  const [error,      setError]      = useState("");
  const [uploading,  setUploading]  = useState(false);
  const [uploadMsg,  setUploadMsg]  = useState("");

  // Fetch the authenticated user on mount
  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) { router.push("/login"); return; }

    axios
      .get(`${API}/users/me`, { headers: { Authorization: `Bearer ${token}` } })
      .then(({ data }) => setUser(data))
      .catch(() => {
        localStorage.removeItem("token");
        router.push("/login");
      });
  }, []);

  const handleResumeUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const token = localStorage.getItem("token");
    const fd    = new FormData();
    fd.append("file", file);

    setUploading(true);
    setError("");

    try {
      const { data } = await axios.post(`${API}/users/me/resume`, fd, {
        headers: { Authorization: `Bearer ${token}` },
      });
      setUser((prev) => ({ ...prev, profile: data.profile }));
      const mrv = data.mrv_score ? ` · MRV Score: ${Math.round(data.mrv_score)}/100` : "";
      const mpi = data.mpi ? ` · MPI: ${data.mpi}/100` : "";
      setUploadMsg(`Resume parsed & enriched${mrv}${mpi}. Redirecting to dashboard…`);
      setTimeout(() => router.push("/dashboard"), 1500);
    } catch (err) {
      setError("Upload failed: " + (err.response?.data?.detail || err.message));
    } finally {
      setUploading(false);
    }
  };

  const handleSignOut = () => {
    localStorage.removeItem("token");
    router.push("/login");
  };

  if (!user) {
    return <div style={styles.loading}>Loading profile…</div>;
  }

  const p     = user.profile || {};
  const skills = p.skills         || [];
  const certs  = p.certifications  || [];

  return (
    <div style={styles.page}>
      {/* ── Header ── */}
      <header style={styles.header}>
        <span style={styles.logo}>Career Navigator</span>
        <nav style={styles.nav}>
          <a href="/dashboard" style={styles.navLink}>Dashboard</a>
          <button onClick={handleSignOut} style={styles.signOut}>Sign Out</button>
        </nav>
      </header>

      <main style={styles.main}>
        {/* ── Hero card ── */}
        <section style={styles.heroCard}>
          <div>
            <h2 style={styles.name}>{p.name || user.full_name || user.email}</h2>
            <p style={styles.role}>{p.current_role || "Role not set"}</p>
            <p style={styles.meta}>
              {p.location         && `📍 ${p.location}`}
              {p.location && p.experience_years != null && " · "}
              {p.experience_years != null && `${p.experience_years} yrs experience`}
            </p>
          </div>

          <label style={styles.uploadBtn}>
            {uploading ? "Uploading…" : "Upload Resume"}
            <input
              type="file"
              accept=".json,.pdf"
              onChange={handleResumeUpload}
              style={{ display: "none" }}
            />
          </label>
        </section>

        {error && <p style={styles.errorBanner}>{error}</p>}
        {uploadMsg && (
          <p style={{
            ...styles.errorBanner,
            background:   "rgba(16,185,129,0.1)",
            borderColor:  "#10b981",
            color:        "#065f46",
          }}>{uploadMsg}</p>
        )}

        {/* ── Info grid ── */}
        <div style={styles.grid}>
          {/* Skills */}
          <section style={styles.card}>
            <h3 style={styles.cardTitle}>Skills</h3>
            {skills.length === 0 ? (
              <p style={styles.empty}>Upload a resume to populate skills.</p>
            ) : (
              skills.map((skill) => (
                <div key={skill} style={styles.skillRow}>
                  <span style={styles.skillLabel}>{skill}</span>
                  <ProgressBar value={75} />
                </div>
              ))
            )}
          </section>

          {/* Certifications */}
          <section style={styles.card}>
            <h3 style={styles.cardTitle}>Certifications</h3>
            {certs.length === 0 ? (
              <p style={styles.empty}>No certifications found in resume.</p>
            ) : (
              certs.map((cert, idx) => {
                const name   = cert.name   || cert;
                const active = cert.status === "Active";
                return (
                  <div key={idx} style={styles.certRow}>
                    <div>
                      <span style={styles.certName}>{name}</span>
                      {cert.issuer && (
                        <span style={styles.certIssuer}> · {cert.issuer}</span>
                      )}
                    </div>
                    <span style={{
                      ...styles.badge,
                      background: active ? "#dcfce7" : "#fef3c7",
                      color:      active ? "#166534" : "#92400e",
                    }}>
                      {cert.status || "Planned"}
                    </span>
                  </div>
                );
              })
            )}
          </section>

          {/* Career target — full width */}
          <section style={{ ...styles.card, gridColumn: "1 / -1" }}>
            <h3 style={styles.cardTitle}>Career Target</h3>
            <p style={styles.targetRole}>
              {p.target_role
                || "Set your target role by uploading a detailed resume."}
            </p>
          </section>
        </div>
      </main>
    </div>
  );
}

// ─── Styles ───────────────────────────────────────────────────────────────────
const styles = {
  page: {
    minHeight:  "100vh",
    background: "#f8fafc",
    fontFamily: "'Segoe UI', system-ui, sans-serif",
  },
  loading: {
    display:        "flex",
    justifyContent: "center",
    alignItems:     "center",
    height:         "100vh",
    fontSize:       18,
    color:          "#64748b",
  },
  header: {
    display:        "flex",
    justifyContent: "space-between",
    alignItems:     "center",
    padding:        "16px 40px",
    background:     "#0f172a",
  },
  logo: { fontSize: 20, fontWeight: 700, color: "#60a5fa" },
  nav:  { display: "flex", alignItems: "center", gap: 24 },
  navLink: {
    color:          "#cbd5e1",
    textDecoration: "none",
    fontSize:       14,
  },
  signOut: {
    background: "transparent",
    border:     "1px solid #475569",
    color:      "#cbd5e1",
    padding:    "6px 14px",
    borderRadius: 6,
    cursor:     "pointer",
    fontSize:   13,
  },
  main: {
    maxWidth: 1000,
    margin:   "40px auto",
    padding:  "0 24px",
  },
  heroCard: {
    background:     "linear-gradient(135deg, #1e3a5f, #2563eb)",
    borderRadius:   12,
    padding:        "32px 40px",
    color:          "#fff",
    display:        "flex",
    justifyContent: "space-between",
    alignItems:     "center",
    marginBottom:   28,
  },
  name: { margin: 0, fontSize: 26, fontWeight: 700 },
  role: { margin: "6px 0 0", fontSize: 16, color: "#bfdbfe" },
  meta: { margin: "8px 0 0", fontSize: 13, color: "#93c5fd" },
  uploadBtn: {
    background:   "#fff",
    color:        "#2563eb",
    padding:      "10px 20px",
    borderRadius: 8,
    cursor:       "pointer",
    fontWeight:   600,
    fontSize:     14,
    whiteSpace:   "nowrap",
  },
  errorBanner: {
    color:        "#dc2626",
    background:   "#fef2f2",
    border:       "1px solid #fecaca",
    borderRadius: 8,
    padding:      "10px 16px",
    marginBottom: 16,
    fontSize:     13,
  },
  grid: {
    display:             "grid",
    gridTemplateColumns: "1fr 1fr",
    gap:                 20,
  },
  card: {
    background:   "#fff",
    borderRadius: 10,
    padding:      "24px 28px",
    boxShadow:    "0 1px 4px rgba(0,0,0,0.08)",
  },
  cardTitle: {
    margin:     "0 0 16px",
    fontSize:   16,
    fontWeight: 700,
    color:      "#0f172a",
  },
  skillRow: {
    display:     "flex",
    alignItems:  "center",
    marginBottom: 12,
    gap:         12,
  },
  skillLabel: {
    width:     160,
    fontSize:  13,
    color:     "#374151",
    flexShrink: 0,
  },
  certRow: {
    display:        "flex",
    justifyContent: "space-between",
    alignItems:     "center",
    marginBottom:   12,
  },
  certName:   { fontSize: 13, color: "#374151", fontWeight: 500 },
  certIssuer: { fontSize: 12, color: "#94a3b8" },
  badge: {
    fontSize:     11,
    fontWeight:   600,
    padding:      "3px 10px",
    borderRadius: 20,
  },
  empty: {
    color:      "#94a3b8",
    fontSize:   13,
    fontStyle:  "italic",
  },
  targetRole: {
    fontSize:   20,
    fontWeight: 600,
    color:      "#1e3a5f",
    margin:     0,
  },
};
