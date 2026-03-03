/**
 * ProgressBar — Phase 1 Component
 *
 * Props:
 *   value  {number}  0–100 fill percentage
 *   color  {string}  optional CSS colour (default: #2563eb)
 *   label  {string}  optional text label rendered inline before the bar
 */
export default function ProgressBar({ value = 0, color = "#2563eb", label }) {
  const clamped = Math.min(100, Math.max(0, value));

  return (
    <div style={styles.wrapper}>
      {label && <span style={styles.label}>{label}</span>}
      <div style={styles.track}>
        <div
          style={{ ...styles.fill, width: `${clamped}%`, background: color }}
          role="progressbar"
          aria-valuenow={clamped}
          aria-valuemin={0}
          aria-valuemax={100}
        />
      </div>
      <span style={styles.pct}>{clamped}%</span>
    </div>
  );
}

const styles = {
  wrapper: {
    display:     "flex",
    alignItems:  "center",
    gap:         8,
    flex:        1,
  },
  label: {
    fontSize:  12,
    color:     "#64748b",
    minWidth:  80,
    flexShrink: 0,
  },
  track: {
    flex:         1,
    height:       8,
    background:   "#e2e8f0",
    borderRadius: 99,
    overflow:     "hidden",
  },
  fill: {
    height:       "100%",
    borderRadius: 99,
    transition:   "width 0.4s ease",
  },
  pct: {
    fontSize:  11,
    color:     "#94a3b8",
    minWidth:  32,
    textAlign: "right",
  },
};
