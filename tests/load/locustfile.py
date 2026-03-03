"""
Locust load test — Career Navigator (Phase 7)
=============================================
Exercises the v1 SQLite API (port 8001) under realistic traffic.

Target SLAs (50 concurrent users):
  Auth endpoints:      p95 < 500 ms,  p99 < 1 s
  Resilience / FAIR:   p95 < 2 s,     p99 < 4 s
  Proctor Q&A:         p95 < 200 ms,  p99 < 500 ms
  Artifact (inline):   p95 < 30 s     (LLM-backed)
  Error rate:          < 0.1 %

Run:
  # Install: pip install locust
  locust -f tests/load/locustfile.py --host=http://localhost:8001

  # Headless (CI):
  locust -f tests/load/locustfile.py --host=http://localhost:8001 \
         --users=50 --spawn-rate=5 --run-time=5m --headless \
         --html=tests/load/report.html --csv=tests/load/results

  # Quick smoke (5 users × 60 s):
  locust -f tests/load/locustfile.py --host=http://localhost:8001 \
         --users=5 --spawn-rate=1 --run-time=60s --headless

User mix (realistic):
  70% AuthedUser        — login → cert catalog → FAIR calc → proctor Q&A
  20% ResilienceUser    — login → full resilience forecast
  10% ArtifactUser      — login → artifact inline generate (throttled)

Environment variables:
  LOAD_TEST_EMAIL    — email prefix for test accounts (default: loadtest)
  LOAD_TEST_PASSWORD — shared password for all test accounts (default: LoadTest1!)
"""
import os
import random
import string
import time

from locust import HttpUser, TaskSet, between, task, events


# ── Configuration ──────────────────────────────────────────────────────────

BASE_EMAIL    = os.getenv("LOAD_TEST_EMAIL",    "loadtest")
BASE_PASSWORD = os.getenv("LOAD_TEST_PASSWORD", "LoadTest1!")

CERT_IDS = ["aigp", "cisa", "aaia", "ciasp"]

FAIR_PAYLOADS = [
    {"tef": 4.0,  "vulnerability": 0.45, "primary_loss": 50_000,  "secondary_loss": 10_000},
    {"tef": 10.0, "vulnerability": 0.15, "primary_loss": 500_000, "secondary_loss": 0},
    {"tef": 1.0,  "vulnerability": 0.8,  "primary_loss": 100_000, "secondary_loss": 5_000},
    {"tef": 2.0,  "vulnerability": 0.6,  "primary_loss": 250_000, "secondary_loss": 25_000},
]

RESUME_PROFILES = [
    {
        "current_role": "IT Audit Manager",
        "years_experience": 8,
        "skills": ["SOX Compliance", "Risk Assessment", "COBIT", "Data Analytics"],
        "certifications": ["CISA"],
        "location": "Los Angeles, CA",
        "market_pressure_index": 62,
    },
    {
        "current_role": "Cybersecurity Analyst",
        "years_experience": 4,
        "skills": ["Penetration Testing", "SIEM", "Threat Intelligence"],
        "certifications": ["CISSP"],
        "location": "Austin, TX",
        "market_pressure_index": 55,
    },
    {
        "current_role": "AI Governance Specialist",
        "years_experience": 3,
        "skills": ["AI Ethics", "Model Risk", "EU AI Act", "Privacy Law"],
        "certifications": ["AIGP"],
        "location": "New York, NY",
        "market_pressure_index": 48,
    },
]


# ── Helpers ────────────────────────────────────────────────────────────────

def _random_suffix(n: int = 6) -> str:
    return "".join(random.choices(string.digits, k=n))


# ── Task Sets ──────────────────────────────────────────────────────────────

class AuthFlow(TaskSet):
    """Register then login — tests bcrypt throughput and JWT issuance."""

    @task
    def register_and_login(self):
        suffix = _random_suffix()
        email  = f"{BASE_EMAIL}+{suffix}@loadtest.example.com"

        # Register
        self.client.post(
            "/auth/register",
            json={"email": email, "password": BASE_PASSWORD, "full_name": "Load Test"},
            name="/auth/register",
        )

        # Login
        resp = self.client.post(
            "/auth/login",
            data={"username": email, "password": BASE_PASSWORD},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            name="/auth/login",
        )
        if resp.ok:
            token = resp.json().get("access_token")
            self.user.token = token

        self.interrupt()


class CatalogFlow(TaskSet):
    """Hit the proctored exam catalog — should be fast and unauthenticated."""

    @task(3)
    def get_catalog(self):
        self.client.get("/api/proctor/catalog", name="/api/proctor/catalog")

    @task(1)
    def stop(self):
        self.interrupt()


class FAIRCalcFlow(TaskSet):
    """Exercise the FAIR risk calculator — purely computational, no LLM."""

    @task(4)
    def fair_calc(self):
        payload = random.choice(FAIR_PAYLOADS)
        self.client.post(
            "/api/resilience/fair-calc",
            json=payload,
            name="/api/resilience/fair-calc",
        )

    @task(1)
    def stop(self):
        self.interrupt()


class ProctorFlow(TaskSet):
    """Full exam session: create → 5 questions → results."""

    def on_start(self):
        self.session_id = None
        self.cert_id    = random.choice(CERT_IDS)

    @task
    def run_session(self):
        headers = {}
        if hasattr(self.user, "token") and self.user.token:
            headers["Authorization"] = f"Bearer {self.user.token}"

        # 1. Create session
        resp = self.client.post(
            "/api/proctor/session/start",
            json={"cert_id": self.cert_id, "mode": "practice"},
            headers=headers,
            name="/api/proctor/session/start",
        )
        if not resp.ok:
            return
        session_id = resp.json().get("session_id")
        if not session_id:
            return

        # 2. Answer 5 questions (not full session — avoids monopolising workers)
        for _ in range(5):
            q_resp = self.client.get(
                f"/api/proctor/session/{session_id}/question",
                headers=headers,
                name="/api/proctor/session/{session_id}/question",
            )
            if not q_resp.ok or "error" in q_resp.json():
                break
            self.client.post(
                f"/api/proctor/session/{session_id}/answer",
                json={"answer_index": random.randint(0, 3)},
                headers=headers,
                name="/api/proctor/session/{session_id}/answer",
            )

        self.interrupt()


class ResilienceFlow(TaskSet):
    """Full resilience + FAIR forecast — heaviest non-LLM endpoint."""

    @task
    def forecast(self):
        profile = random.choice(RESUME_PROFILES)
        headers = {}
        if hasattr(self.user, "token") and self.user.token:
            headers["Authorization"] = f"Bearer {self.user.token}"

        self.client.post(
            "/api/resilience/forecast",
            json={"profile": profile, "market": random.choice(["US", "IN"])},
            headers=headers,
            name="/api/resilience/forecast",
        )
        self.interrupt()


# ── User types ─────────────────────────────────────────────────────────────

class AuthedUser(HttpUser):
    """
    70% of traffic.
    Logs in once then cycles through catalog, FAIR calc, and proctor.
    """
    weight       = 70
    wait_time    = between(1, 4)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.token = None

    def on_start(self):
        """Authenticate once at start of each virtual user's session."""
        suffix = _random_suffix()
        email  = f"{BASE_EMAIL}+{suffix}@loadtest.example.com"

        self.client.post(
            "/auth/register",
            json={"email": email, "password": BASE_PASSWORD, "full_name": "Load Test"},
            name="/auth/register [setup]",
        )
        resp = self.client.post(
            "/auth/login",
            data={"username": email, "password": BASE_PASSWORD},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            name="/auth/login [setup]",
        )
        if resp.ok:
            self.token = resp.json().get("access_token")

    @task(5)
    def catalog(self):
        self.client.get("/api/proctor/catalog", name="/api/proctor/catalog")

    @task(4)
    def fair_calc(self):
        self.client.post(
            "/api/resilience/fair-calc",
            json=random.choice(FAIR_PAYLOADS),
            name="/api/resilience/fair-calc",
        )

    @task(3)
    def proctor_question(self):
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        cert    = random.choice(CERT_IDS)
        resp = self.client.post(
            "/api/proctor/session/start",
            json={"cert_id": cert, "mode": "practice"},
            headers=headers,
            name="/api/proctor/session/start",
        )
        if not resp.ok:
            return
        sid = resp.json().get("session_id")
        if sid:
            self.client.get(
                f"/api/proctor/session/{sid}/question",
                headers=headers,
                name="/api/proctor/session/{session_id}/question",
            )

    @task(1)
    def health(self):
        self.client.get("/health", name="/health")


class ResilienceUser(HttpUser):
    """
    20% of traffic — heavier endpoint, longer think time.
    """
    weight    = 20
    wait_time = between(3, 8)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.token = None

    def on_start(self):
        suffix = _random_suffix()
        email  = f"{BASE_EMAIL}+r{suffix}@loadtest.example.com"
        self.client.post(
            "/auth/register",
            json={"email": email, "password": BASE_PASSWORD, "full_name": "Resilience User"},
            name="/auth/register [setup]",
        )
        resp = self.client.post(
            "/auth/login",
            data={"username": email, "password": BASE_PASSWORD},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            name="/auth/login [setup]",
        )
        if resp.ok:
            self.token = resp.json().get("access_token")

    @task
    def forecast(self):
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        self.client.post(
            "/api/resilience/forecast",
            json={
                "profile": random.choice(RESUME_PROFILES),
                "market":  random.choice(["US", "IN"]),
            },
            headers=headers,
            name="/api/resilience/forecast",
        )

    @task(2)
    def fair_calc(self):
        self.client.post(
            "/api/resilience/fair-calc",
            json=random.choice(FAIR_PAYLOADS),
            name="/api/resilience/fair-calc",
        )


class ArtifactUser(HttpUser):
    """
    10% of traffic — LLM-backed endpoint, very long wait time.
    Simulates the heaviest use case: artifact generation.
    """
    weight    = 10
    wait_time = between(30, 90)  # throttle: max 2 req/min per user

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.token = None

    def on_start(self):
        suffix = _random_suffix()
        email  = f"{BASE_EMAIL}+a{suffix}@loadtest.example.com"
        self.client.post(
            "/auth/register",
            json={"email": email, "password": BASE_PASSWORD, "full_name": "Artifact User"},
            name="/auth/register [setup]",
        )
        resp = self.client.post(
            "/auth/login",
            data={"username": email, "password": BASE_PASSWORD},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            name="/auth/login [setup]",
        )
        if resp.ok:
            self.token = resp.json().get("access_token")

    @task
    def generate_artifact(self):
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        self.client.post(
            "/api/artifacts/inline",
            json={
                "cert_id":       random.choice(CERT_IDS),
                "artifact_type": random.choice(["cheat_sheet", "practice_exam"]),
                "question_id":   None,
            },
            headers=headers,
            name="/api/artifacts/inline",
            timeout=60,  # LLM calls can take up to 30 s
        )


# ── Event hooks ────────────────────────────────────────────────────────────

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    print("\n" + "=" * 60)
    print("Career Navigator Load Test — Phase 7")
    print("Target: http://localhost:8001")
    print("SLAs: p95 < 500ms (auth), < 2s (resilience), < 200ms (proctor)")
    print("=" * 60 + "\n")


@events.quitting.add_listener
def on_quitting(environment, **kwargs):
    stats = environment.stats.total
    print("\n" + "=" * 60)
    print("Load Test Complete")
    print(f"  Requests:    {stats.num_requests:,}")
    print(f"  Failures:    {stats.num_failures:,} ({stats.fail_ratio * 100:.2f}%)")
    print(f"  RPS (avg):   {stats.total_rps:.1f}")
    print(f"  p50:         {stats.get_response_time_percentile(0.5):.0f} ms")
    print(f"  p95:         {stats.get_response_time_percentile(0.95):.0f} ms")
    print(f"  p99:         {stats.get_response_time_percentile(0.99):.0f} ms")

    fail_pct = stats.fail_ratio * 100
    p95      = stats.get_response_time_percentile(0.95)

    if fail_pct > 0.1:
        print(f"\n  ⚠ FAIL: error rate {fail_pct:.2f}% exceeds 0.1% SLA")
        environment.process_exit_code = 1
    elif p95 > 2000:
        print(f"\n  ⚠ FAIL: p95 {p95:.0f}ms exceeds 2,000ms SLA")
        environment.process_exit_code = 1
    else:
        print("\n  PASS: all SLAs met")

    print("=" * 60 + "\n")
