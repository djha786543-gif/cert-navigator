# Career Navigator — Resilience-Linked Career Engine

> AI-powered career portal for IT Audit and AI Governance professionals.
> Personalised job recommendations · FAIR risk modelling · Adaptive exam simulation · 5-year disruption forecast

**Live stack:** FastAPI + PostgreSQL/pgvector + Celery/Redis + Next.js · **80/80 tests passing**

---

## What it does

Career Navigator answers one question for senior IT auditors and AI governance professionals:

> *"Is my career resilient enough to survive the AI transition — and what do I do next?"*

| Feature | Description |
|---------|-------------|
| **Disruption Forecast** | FAIR risk model quantifies career exposure ($ALE/year). 5-year action vs. inaction scenarios. |
| **Resilience Score** | Per-skill automation risk + MRV (Market Resilience Value) composite score 0–100. |
| **Study Vault** | AI-generated study guides, cheat sheets, and 10-MCQ practice exams for AIGP / CISA / AAIA / CIASP. |
| **Simulation Mode** | Adaptive proctored exam sessions with IRT-sigmoid readiness scoring and weakness tracking. |
| **Job Engine** | Live Adzuna job search (US + India markets) with cert-weighted ranking and daily refresh. |
| **Market Intelligence** | Salary bands, demand index, and Gold Standard cert priority by market. |

---

## Architecture

```
Internet
   │
   ▼
Nginx (reverse proxy, rate limiting)
   ├── /api/*  → FastAPI (uvicorn --workers 4)   ← port 8001
   └── /*      → Next.js frontend                ← port 3000

FastAPI
   ├── src/backend/         v1 — SQLite, live dev stack
   │   ├── user_management.py    JWT auth + resume ingestion
   │   ├── api_routes.py         all API endpoints (inline, no Celery)
   │   └── agents/
   │       ├── resilience_forecaster_agent.py   FAIR model + disruption
   │       ├── artifact_sovereign_agent.py      study guides + practice exams
   │       ├── proctor_agent.py                 adaptive exam sessions (IRT)
   │       ├── market_intelligence_agent.py     salary + demand data
   │       └── resume_inference_agent.py        MRV + skill trajectory
   │
   └── backend/app/         v2 — PostgreSQL + pgvector + Celery
       ├── routers/          async FastAPI routers
       ├── services/         auth, resume parser, skill vectorizer
       ├── workers/          Celery tasks (heavy: PDF, LLM, bulk scrape)
       └── middleware/       Prometheus metrics, structured logging, circuit breaker

PostgreSQL 16 + pgvector   ← skill embeddings (all-MiniLM-L6-v2, 384-dim, HNSW index)
Redis 7                    ← Celery broker + result backend + job cache TTLs
```

---

## Quick Start (local dev — no Docker required)

```bash
git clone https://github.com/djha786543-gif/cert-navigator
cd cert-navigator

# 1. Python environment
python -m venv career_env
source career_env/Scripts/activate      # Windows
pip install -r requirements.txt

# 2. Environment
cp .env.example .env
# Edit .env — set SECRET_KEY at minimum

# 3. Start backend (SQLite v1, no Docker needed)
uvicorn src.backend.main:app --reload --port 8001

# 4. Start frontend (separate terminal)
cd frontend && npm install && npm run dev

# Open: http://localhost:3000
# Demo login: dj@careernavigator.ai / Demo1234
```

---

## Full Stack (Docker Compose)

```bash
cp .env.example .env    # fill in POSTGRES_PASSWORD, SECRET_KEY, API keys

# Dev stack (API + Worker + Postgres + Redis + Frontend)
docker compose up --build

# With monitoring (Prometheus + Grafana)
docker compose -f docker-compose.yml -f docker-compose.monitoring.yml up -d
# Grafana: http://localhost:3001  (admin/admin)
# Flower:  http://localhost:5555
```

---

## API Reference

All endpoints except `/health`, `/api/proctor/catalog`, and `/api/resilience/fair-calc` require:
```
Authorization: Bearer <jwt_token>
```

### Auth
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/auth/register` | Create account `{"email","password","full_name"}` |
| `POST` | `/auth/login` | Login → `{"access_token", "token_type"}` |
| `GET`  | `/users/me` | Authenticated user profile |
| `POST` | `/users/me/resume` | Upload JSON or PDF resume |

### Resilience (Phase 4)
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/resilience/forecast` | Full FAIR model + 5-year forecast + skill audit |
| `POST` | `/api/resilience/fair-calc` | Standalone FAIR calculator (TEF × Vuln × SLE) |

### Study Vault (Phase 3)
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/api/artifacts/catalog` | Available artifact types per cert |
| `POST` | `/api/artifacts/inline` | Generate artifact synchronously (study guide / cheat sheet / practice exam) |
| `POST` | `/api/artifacts/generate` | Queue artifact via Celery (async) |
| `GET`  | `/api/artifacts/task/{task_id}` | Poll Celery task status |

### Simulation Mode (Phase 5)
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/proctor/session/start` | Start practice or exam session |
| `GET`  | `/api/proctor/session/{id}/question` | Get current question (answer hidden) |
| `POST` | `/api/proctor/session/{id}/answer` | Submit answer → immediate feedback (practice) or deferred (exam) |
| `GET`  | `/api/proctor/session/{id}/results` | Full results + IRT readiness score |
| `GET`  | `/api/proctor/weakness` | Cross-session weakness report by domain |
| `GET`  | `/api/proctor/catalog` | Cert catalog with question counts |

### Jobs (Phase 2)
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/api/jobs/me` | Ranked personalised job list |
| `POST` | `/api/jobs/refresh` | Force-refresh job cache |
| `GET`  | `/api/jobs/market-intel` | Salary bands + demand index |

---

## Certifications Supported

| ID | Credential | Issuer | Questions |
|----|-----------|--------|-----------|
| `aigp` | AI Governance Professional | IAPP | 20 |
| `cisa` | Certified Information Systems Auditor | ISACA | 15 |
| `aaia` | Associate AI Auditor | ISACA | 10 |
| `ciasp` | Certified Internal Auditor — Security+ | IIA | 10 |

Each certification has: exam metadata · domain weights · study resources · adaptive question bank · IRT readiness model.

---

## Monitoring

```bash
make monitor          # Start Prometheus + Grafana + exporters
make monitor-down     # Stop monitoring stack
```

| Service | URL | Credentials |
|---------|-----|-------------|
| Grafana dashboards | http://localhost:3001 | admin / admin |
| Prometheus | http://localhost:9090 | — |
| Flower (Celery) | http://localhost:5555 | admin / admin |
| API metrics (scrape) | http://localhost:8001/metrics | — |

**Key metrics tracked:** `http_requests_total`, `http_request_duration_seconds` (p50/p95/p99), `celery_task_total`, `proctor_active_sessions`, `circuit_breaker_open{service}`.

**Alerts configured:** APIDown, HighErrorRate (>1%), SlowP95 (>2s), CircuitBreakerOpen, PostgresConnectionsHigh, RedisMemoryHigh.

---

## Testing

```bash
make test-unit          # 64 unit tests (no DB, no network)
make test-integration   # 8 integration tests (FastAPI TestClient)
make test               # all 80 tests

make load-test          # Locust: 50 users × 5 min (requires backend running)
make load-test-smoke    # Quick smoke: 5 users × 60s
```

**Test coverage:**

| Suite | Tests | Covers |
|-------|-------|--------|
| `test_circuit_breaker.py` | 16 | State transitions, HALF_OPEN probe, decorator, pre-built breakers |
| `test_proctor_agent.py` | 33 | Session lifecycle, adaptive difficulty, IRT readiness, weakness report |
| `test_resilience_agent.py` | 23 | FAIR model (8 parametric cases), forecast structure, skill audit |
| `test_health.py` | 8 | Health endpoints, auth gates, FAIR calc validation |

---

## AWS Deployment (Terraform)

```bash
cd terraform

# Configure secrets (never commit these)
export TF_VAR_secret_key=$(python -c "import secrets; print(secrets.token_hex(32))")
export TF_VAR_db_password="<strong-password>"
export TF_VAR_anthropic_api_key="<your-key>"

# Edit prod.tfvars — set api_image, frontend_image (GHCR URLs from CI/CD)

terraform init
make terraform-plan     # review changes
make terraform-apply    # deploy
```

**Infrastructure:** ECS Fargate (API ×2 + Worker ×1) · RDS PostgreSQL 16 Multi-AZ · ElastiCache Redis 7 · S3 artifact storage · ALB with autoscaling · Secrets Manager · CloudWatch logs.

**Estimated cost (50 users, us-west-2):** ~$244/month.

---

## Make Commands

```
make dev              Start v1 SQLite backend + Next.js frontend (local)
make dev-v2           Start full v2 Docker stack
make test             Run all 80 tests
make lint             Ruff lint check
make monitor          Start Prometheus + Grafana
make load-test        Locust 50-user load test
make backup           PostgreSQL backup → ./backups/
make migrate          Apply Alembic migrations
make terraform-plan   Preview AWS infrastructure changes
make help             Full command reference
```

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SECRET_KEY` | Yes | `change-me` | JWT signing key (≥ 32 hex chars) |
| `DATABASE_URL` | No | SQLite | PostgreSQL connection string |
| `REDIS_URL` | No | — | Redis for Celery + cache |
| `ANTHROPIC_API_KEY` | No | — | Claude API for artifact generation |
| `ADZUNA_APP_ID` | No | — | Job search API (free: 250 req/day) |
| `ADZUNA_APP_KEY` | No | — | Adzuna API key |
| `DEBUG` | No | `false` | Enable debug logging |

Full reference: [`.env.example`](.env.example)

---

## Capacity (50 Concurrent Users)

| Bottleneck | Impact | Mitigation |
|-----------|--------|------------|
| Embedding model 600 MB/worker | 2.4 GB RAM at 4 workers | `--workers 2` on < 8 GB RAM |
| Bcrypt 250 ms/hash | 16 logins/sec max | 8-hour JWT TTL, rate-limit auth |
| LLM artifacts 15–30 s | Celery queue depth | Cache 24h, Lambda at > 200/day |
| Adzuna 250 req/day free | Saturates at 84 users | Redis cache (4h TTL), upgrade tier |
| pgvector HNSW | Fine to 1M users | Supabase at > 10K users |

Full analysis: [`docs/CAPACITY_PLAN.md`](docs/CAPACITY_PLAN.md)

---

## Project Structure

```
cert-navigator/
├── src/backend/             v1 — SQLite live stack (port 8001)
│   ├── user_management.py
│   ├── api_routes.py
│   └── agents/              6 specialist AI agents
├── backend/app/             v2 — PostgreSQL + pgvector + Celery
│   ├── routers/             async FastAPI endpoints
│   ├── services/            auth, resume, embeddings
│   ├── workers/             Celery tasks
│   ├── metrics.py           Prometheus instrumentation
│   └── middleware/          request logging, circuit breaker
├── frontend/                Next.js (6-tab dashboard)
├── tests/
│   ├── unit/                64 fast tests
│   ├── integration/         8 TestClient tests
│   └── load/                Locust scenarios
├── monitoring/              Prometheus + Grafana configs + alerts
├── terraform/               AWS ECS/RDS/Redis/S3 IaC
├── nginx/                   Reverse proxy + rate limiting
├── docs/
│   ├── CAPACITY_PLAN.md
│   ├── DEPLOYMENT_CHECKLIST.md
│   └── runbooks/
├── docker-compose.yml
├── docker-compose.prod.yml
├── docker-compose.monitoring.yml
├── Makefile
└── .github/workflows/       CI (lint + test + build) + CD + security scan
```

---

## CI/CD

| Workflow | Trigger | Jobs |
|----------|---------|------|
| `ci.yml` | Every push + PR | ruff lint · pytest unit · Next.js build |
| `cd.yml` | Push to `main` | Build Docker images → GHCR → SSH deploy (rolling restart) |
| `security.yml` | Every push + weekly | bandit SAST · pip-audit CVE · detect-secrets · tfsec |

---

## Phase History

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | SQLite auth, JWT, resume ingestion | ✅ |
| 2 | Job engine (US/IN), MarketIntelligenceAgent, Gold Standard dashboard | ✅ |
| 3 | ArtifactSovereignAgent — study guides, cheat sheets, practice exams | ✅ |
| 4 | ResilienceForecasterAgent — FAIR model, 5-year forecast, MRV scoring | ✅ |
| 5 | ProctorAgent — adaptive difficulty (IRT), Simulation Mode tab | ✅ |
| 6 | Docker, Nginx, Alembic, GitHub Actions CI/CD, Makefile, 64 tests | ✅ |
| 7 | Prometheus/Grafana, circuit breaker, Locust, Terraform (AWS), security CI, 80 tests | ✅ |

---

*Built by Deobrat Jha — IT Audit Manager, with Claude Code (Anthropic).*

---

## Skills Gap Analyzer v2 Formula

Per role requirement:
- `effective_proficiency = proficiency * decay(last_used_at)`
- `gap = max(0, required_level - effective_proficiency)`
- `priority_score = gap * importance_weight * demand_multiplier * critical_multiplier`
- `estimated_hours = ceil(baseline_learning_hours * gap * demand_multiplier)`

Confidence:
- `0.35*coverage + 0.25*recency + 0.20*evidence + 0.15*role_quality + 0.05*gap_density`
- bounded to `[0,1]`

Decay:
- exponential with a 12-month half-life
