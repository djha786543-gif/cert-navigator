/**
 * TimelineCard — Phase 4 Component
 *
 * Renders a single year of the 5-year career roadmap as a vertical timeline node.
 *
 * Props:
 *   year         {object}    A single year object from career_plan.generate_career_plan()
 *   isActive     {boolean}   True if this is the current/highlighted year
 *   isLast       {boolean}   True for the final node (hides the connector line below)
 */
const PHASE_COLOURS = {
  Establish:  { bg: "#dbeafe", accent: "#2563eb", text: "#1e40af" },
  Expand:     { bg: "#dcfce7", accent: "#16a34a", text: "#166534" },
  Lead:       { bg: "#fef3c7", accent: "#d97706", text: "#92400e" },
  Direct:     { bg: "#f3e8ff", accent: "#7c3aed", text: "#5b21b6" },
  Transform:  { bg: "#fee2e2", accent: "#dc2626", text: "#991b1b" },
};

export default function TimelineCard({ year, isActive = false, isLast = false }) {
  if (!year) return null;

  const colours = PHASE_COLOURS[year.phase] || PHASE_COLOURS.Establish;
  const salary  = year.salary_range || {};

  return (
    <div style={styles.row}>
      {/* ── Left column: connector + node ── */}
      <div style={styles.leftCol}>
        <div style={{
          ...styles.node,
          background:  isActive ? colours.accent : "#fff",
          border:      `3px solid ${colours.accent}`,
          color:       isActive ? "#fff" : colours.accent,
        }}>
          {year.year}
        </div>
        {!isLast && <div style={{ ...styles.connector, borderColor: colours.accent }} />}
      </div>

      {/* ── Right column: card content ── */}
      <div style={{
        ...styles.card,
        background:  isActive ? colours.bg : "#fff",
        border:      `1px solid ${isActive ? colours.accent : "#e2e8f0"}`,
        boxShadow:   isActive ? `0 4px 20px ${colours.accent}33` : "0 1px 4px rgba(0,0,0,0.06)",
      }}>
        {/* Header */}
        <div style={styles.cardHeader}>
          <div>
            <span style={{ ...styles.phaseBadge, background: colours.accent }}>
              {year.phase} · {year.year_label}
            </span>
            <h3 style={{ ...styles.roleTitle, color: colours.text }}>{year.target_role}</h3>
          </div>
          <div style={styles.salaryBox}>
            <span style={styles.salaryLabel}>Target Salary</span>
            <span style={{ ...styles.salaryRange, color: colours.accent }}>
              ${(salary.min / 1000).toFixed(0)}K – ${(salary.max / 1000).toFixed(0)}K
            </span>
          </div>
        </div>

        {/* Certifications */}
        {year.certifications_to_earn?.length > 0 && (
          <div style={styles.section}>
            <p style={styles.sectionLabel}>🎓 Certifications to Earn</p>
            <div style={styles.tagRow}>
              {year.certifications_to_earn.map((c) => (
                <span key={c} style={{ ...styles.certTag, background: colours.accent }}>{c}</span>
              ))}
            </div>
          </div>
        )}

        {/* Milestones */}
        <div style={styles.section}>
          <p style={styles.sectionLabel}>🏁 Key Milestones</p>
          <ul style={styles.list}>
            {year.key_milestones?.slice(0, 3).map((m, i) => (
              <li key={i} style={styles.listItem}>
                <span style={{ ...styles.bullet, color: colours.accent }}>▸</span> {m}
              </li>
            ))}
          </ul>
        </div>

        {/* Skills */}
        <div style={styles.section}>
          <p style={styles.sectionLabel}>🛠 Skills to Develop</p>
          <div style={styles.tagRow}>
            {year.skills_to_develop?.slice(0, 4).map((s) => (
              <span key={s} style={styles.skillTag}>{s}</span>
            ))}
          </div>
        </div>

        {/* Action items — collapsed by default; expand to show */}
        <details style={styles.details}>
          <summary style={{ ...styles.summary, color: colours.accent }}>
            View {year.action_items?.length} Action Items &amp; Success Metrics
          </summary>
          <div style={styles.detailsBody}>
            <p style={styles.sectionLabel}>📋 Action Items</p>
            <ul style={styles.list}>
              {year.action_items?.map((a, i) => (
                <li key={i} style={styles.listItem}>
                  <span style={{ color: colours.accent }}>✓</span> {a}
                </li>
              ))}
            </ul>
            <p style={{ ...styles.sectionLabel, marginTop: 12 }}>✅ Success Metrics</p>
            <ul style={styles.list}>
              {year.success_metrics?.map((s, i) => (
                <li key={i} style={styles.listItem}>
                  <span style={{ color: colours.accent }}>◆</span> {s}
                </li>
              ))}
            </ul>
          </div>
        </details>
      </div>
    </div>
  );
}

// ─── Styles ───────────────────────────────────────────────────────────────────
const styles = {
  row: {
    display:  "flex",
    gap:      24,
    position: "relative",
  },
  leftCol: {
    display:        "flex",
    flexDirection:  "column",
    alignItems:     "center",
    width:          48,
    flexShrink:     0,
  },
  node: {
    width:         42,
    height:        42,
    borderRadius:  "50%",
    display:       "flex",
    alignItems:    "center",
    justifyContent:"center",
    fontWeight:    700,
    fontSize:      14,
    zIndex:        1,
    flexShrink:    0,
  },
  connector: {
    width:       2,
    flex:        1,
    borderLeft:  "2px dashed",
    marginTop:   4,
    minHeight:   40,
  },
  card: {
    flex:         1,
    borderRadius: 12,
    padding:      "20px 24px",
    marginBottom: 24,
  },
  cardHeader: {
    display:        "flex",
    justifyContent: "space-between",
    alignItems:     "flex-start",
    marginBottom:   16,
    flexWrap:       "wrap",
    gap:            12,
  },
  phaseBadge: {
    color:        "#fff",
    fontSize:     11,
    fontWeight:   700,
    padding:      "3px 10px",
    borderRadius: 20,
    letterSpacing: "0.05em",
    textTransform: "uppercase",
  },
  roleTitle: {
    margin:     "6px 0 0",
    fontSize:   18,
    fontWeight: 700,
  },
  salaryBox: {
    textAlign: "right",
  },
  salaryLabel: {
    display:    "block",
    fontSize:   11,
    color:      "#94a3b8",
    marginBottom: 2,
  },
  salaryRange: {
    fontSize:   16,
    fontWeight: 700,
  },
  section: {
    marginBottom: 12,
  },
  sectionLabel: {
    fontSize:    12,
    fontWeight:  700,
    color:       "#64748b",
    margin:      "0 0 6px",
    textTransform: "uppercase",
    letterSpacing: "0.04em",
  },
  tagRow: {
    display:  "flex",
    flexWrap: "wrap",
    gap:      6,
  },
  certTag: {
    color:        "#fff",
    fontSize:     12,
    fontWeight:   600,
    padding:      "4px 12px",
    borderRadius: 20,
  },
  skillTag: {
    background:   "#f1f5f9",
    color:        "#475569",
    fontSize:     12,
    padding:      "4px 10px",
    borderRadius: 20,
  },
  list: {
    margin:  0,
    padding: 0,
    listStyle: "none",
  },
  listItem: {
    fontSize:     13,
    color:        "#374151",
    marginBottom: 5,
    display:      "flex",
    gap:          6,
    lineHeight:   "1.4",
  },
  bullet: {
    flexShrink: 0,
    fontWeight: 700,
  },
  details: {
    marginTop: 8,
  },
  summary: {
    fontSize:   13,
    fontWeight: 600,
    cursor:     "pointer",
    userSelect: "none",
  },
  detailsBody: {
    marginTop: 12,
    paddingTop: 12,
    borderTop:  "1px solid #f1f5f9",
  },
};
