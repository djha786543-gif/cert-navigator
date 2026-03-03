# Career Navigator — Capacity Plan (50 Concurrent Users)

**Last updated:** 2026-03-01
**Status:** Phase 7 — Production Hardening

---

## Target SLAs

| Endpoint category | p95 target | p99 target | Error rate |
|-------------------|-----------|-----------|------------|
| Auth (login/register) | < 500 ms | < 1 s | < 0.1% |
| Catalog / health | < 50 ms  | < 100 ms | < 0.01% |
| FAIR calculator | < 200 ms | < 500 ms | < 0.1% |
| Resilience forecast | < 2 s | < 4 s | < 0.1% |
| Proctor Q&A | < 200 ms | < 500 ms | < 0.1% |
| Artifact inline (LLM) | < 30 s | < 60 s | < 1% |

---

## Bottleneck Analysis

### 1. Sentence-Transformers Model (CRITICAL)
- **Size:** 600 MB per worker process
- **Load:** 4 workers × 600 MB = **2.4 GB RAM** baseline
- **Mitigation:**
  - `--workers 1` on machines with < 8 GB RAM (reduces throughput but saves memory)
  - Model is loaded once at startup (`warm_up()`) — no per-request cold start
  - Move to a dedicated embedding service (e.g. `sentence-transformers/api`) to share one model across workers
- **Scale trigger:** If RAM > 80% on p50 load → reduce workers or upgrade instance

### 2. Bcrypt Hashing (HIGH)
- **Cost:** ~250 ms per hash (work factor 12)
- **Throughput:** 4 workers × 4 threads = ~16 logins/sec maximum
- **Mitigation:**
  - JWT tokens have 8-hour TTL — users log in once per session
  - Nginx rate-limits auth to 5 req/min per IP
  - 50 concurrent users → worst case: 50 logins in first minute = 0.83/sec (well within capacity)
- **Scale trigger:** If login p95 > 1 s → reduce work factor to 10 or add a bcrypt worker pool

### 3. Celery LLM Artifacts (HIGH)
- **Latency:** 15–30 s per artifact (Claude Sonnet / GPT-4o)
- **Concurrency:** `--concurrency=2` locally, 4 in production Docker
- **Cost:** ~$0.12 per artifact at current API pricing
- **Mitigation:**
  - Rate-limit artifact generation: 5 concurrent requests via Celery queue
  - Cache artifacts: same cert_id + artifact_type → serve from cache (TTL 24h)
  - At > 200 artifacts/day: migrate to AWS Lambda + SQS (pay per invocation)
- **Scale trigger:** Celery queue depth > 10 for > 5 minutes → scale workers

### 4. PostgreSQL Connection Pool (MEDIUM)
- **Pool size:** asyncpg default = 20 connections
- **Risk:** 4 workers × 5 connections each = 20 connections saturated at peak
- **Mitigation:**
  - Add PgBouncer in transaction mode to multiplex connections
  - `pool_size=5` per worker is sufficient for 50 users (async I/O multiplexes well)
  - Monitor `pg_stat_activity` — alert if > 18/20 connections
- **Scale trigger:** `pg_stat_activity_count > 18` for > 2 minutes

### 5. Adzuna Job API (MEDIUM)
- **Rate limit:** 250 req/day (free tier)
- **Saturation point:** 250 / 50 users = 5 req/user/day → saturates at ~84 users
- **Mitigation:**
  - Cache job results in Redis (TTL 4 hours)
  - Circuit breaker auto-trips after 5 failures
  - Fallback to cached results when circuit is open
- **Scale trigger:** Adzuna 429 responses → upgrade to paid tier ($99/month = 10K req/day)

### 6. In-Memory Proctor Sessions (LOW)
- **Storage:** ~5 KB per active session × 100 sessions = 500 KB (negligible)
- **TTL:** 35 minutes auto-expiry
- **Risk:** Sessions lost on worker restart (single-process only)
- **Mitigation for multi-worker:**
  - Store sessions in Redis: `SETEX session:{id} 2100 {data}`
  - This is the v2 async router path (uses DB for persistence)
- **Scale trigger:** > 500 concurrent sessions → migrate to Redis-backed sessions

---

## Load Test Results (Baseline — 2026-03-01)

Run with: `locust --users=50 --spawn-rate=5 --run-time=5m`

| Endpoint | Requests | Failures | p50 | p95 | p99 | RPS |
|----------|----------|----------|-----|-----|-----|-----|
| /health | - | - | < 5ms | < 10ms | < 20ms | unlimited |
| /auth/login | - | - | *TBD* | *TBD* | *TBD* | *TBD* |
| /api/resilience/fair-calc | - | - | *TBD* | *TBD* | *TBD* | *TBD* |
| /api/proctor/session/start | - | - | *TBD* | *TBD* | *TBD* | *TBD* |

> Run `make load-test` to populate this table with actual measurements.

---

## Scaling Playbook

### Vertical Scaling (immediate — no code change)
```bash
# Reduce embedding workers if RAM is constrained
uvicorn backend.app.main:app --workers 2 --port 8001

# Or Docker (edit docker-compose.yml):
# command: uvicorn backend.app.main:app --workers 2 ...
```

### Horizontal Scaling (Docker Compose)
```bash
# Scale API to 3 replicas behind a load balancer
docker-compose up --scale api=3

# Scale Celery workers for more artifact throughput
docker-compose up --scale worker=3
```

### Database Scaling
```bash
# Add PgBouncer (transaction pooling):
docker-compose up pgbouncer

# Increase RDS instance class (AWS):
terraform apply -var="rds_instance_class=db.r6g.large"
```

### Cache Artifact Responses
```python
# In api_routes.py artifact endpoint:
cache_key = f"artifact:{cert_id}:{artifact_type}"
cached = redis_client.get(cache_key)
if cached:
    return json.loads(cached)
result = await generate_artifact(...)
redis_client.setex(cache_key, 86400, json.dumps(result))  # 24h TTL
return result
```

---

## Monitoring Thresholds → Alerts → Actions

| Metric | Warning | Critical | Action |
|--------|---------|----------|--------|
| RAM usage | > 70% | > 85% | Reduce `--workers` or upgrade instance |
| CPU usage | > 60% (5 min) | > 80% (1 min) | Scale horizontally |
| p95 latency | > 1 s | > 2 s | Investigate slow queries, add caching |
| Error rate | > 0.5% | > 1% | Check logs, circuit breakers |
| DB connections | > 15/20 | > 18/20 | Add PgBouncer |
| Redis memory | > 200 MB | > 240 MB | Flush expired keys, upgrade node |
| Celery queue | > 5 tasks | > 10 tasks | Scale workers |
| Adzuna 429 rate | > 10/day | > 50/day | Upgrade API tier |
