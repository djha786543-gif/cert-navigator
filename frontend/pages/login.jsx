/**
 * Login Page — Phase 1
 * POST /auth/login → stores Bearer JWT in localStorage → redirects to /dashboard
 */
import { useState } from "react";
import { useRouter } from "next/router";
import axios from "axios";

const API = process.env.NEXT_PUBLIC_API_URL || 'https://cert-navigator-production.up.railway.app';

export default function Login() {
  const router  = useRouter();
  const [form,    setForm]    = useState({ email: "", password: "" });
  const [error,   setError]   = useState("");
  const [loading, setLoading] = useState(false);

  const handleChange = (e) =>
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      // FastAPI OAuth2PasswordRequestForm expects URL-encoded body
      const params = new URLSearchParams();
      params.append("username", form.email);
      params.append("password", form.password);

      const { data } = await axios.post(`${API}/auth/login`, params);
      localStorage.setItem("token", data.access_token);
      router.push("/dashboard");
    } catch (err) {
      setError(err.response?.data?.detail || "Login failed. Check your credentials.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={styles.container}>
      <div style={styles.card}>
        <h1 style={styles.title}>Career Navigator</h1>
        <p style={styles.subtitle}>Sign in to your portal</p>

        <form onSubmit={handleSubmit} style={styles.form}>
          <input
            style={styles.input}
            type="email"
            name="email"
            placeholder="Email address"
            value={form.email}
            onChange={handleChange}
            required
            autoComplete="email"
          />
          <input
            style={styles.input}
            type="password"
            name="password"
            placeholder="Password"
            value={form.password}
            onChange={handleChange}
            required
            autoComplete="current-password"
          />

          {error && <p style={styles.error}>{error}</p>}

          <button style={styles.button} type="submit" disabled={loading}>
            {loading ? "Signing in…" : "Sign In"}
          </button>
        </form>

        <p style={styles.footer}>
          No account?{" "}
          <a href="/register" style={styles.anchor}>Register here</a>
        </p>
      </div>
    </div>
  );
}

const styles = {
  container: {
    minHeight:      "100vh",
    display:        "flex",
    alignItems:     "center",
    justifyContent: "center",
    background:     "linear-gradient(135deg, #0f172a 0%, #1e3a5f 100%)",
    fontFamily:     "'Segoe UI', system-ui, sans-serif",
  },
  card: {
    background:   "#fff",
    borderRadius: 12,
    padding:      "40px 48px",
    width:        380,
    boxShadow:    "0 20px 60px rgba(0,0,0,0.3)",
  },
  title: {
    margin:     0,
    fontSize:   28,
    color:      "#0f172a",
    fontWeight: 700,
  },
  subtitle: {
    color:        "#64748b",
    marginTop:    6,
    marginBottom: 28,
    fontSize:     14,
  },
  form: {
    display:       "flex",
    flexDirection: "column",
    gap:           14,
  },
  input: {
    padding:      "12px 14px",
    border:       "1px solid #e2e8f0",
    borderRadius: 8,
    fontSize:     14,
    outline:      "none",
    transition:   "border-color 0.2s",
  },
  button: {
    padding:      "13px",
    background:   "#2563eb",
    color:        "#fff",
    border:       "none",
    borderRadius: 8,
    fontSize:     15,
    fontWeight:   600,
    cursor:       "pointer",
    marginTop:    4,
    transition:   "background 0.2s",
  },
  error: {
    color:     "#dc2626",
    fontSize:  13,
    margin:    0,
  },
  footer: {
    textAlign:  "center",
    marginTop:  20,
    color:      "#64748b",
    fontSize:   13,
  },
  anchor: {
    color:          "#2563eb",
    textDecoration: "none",
    fontWeight:     600,
  },
};
