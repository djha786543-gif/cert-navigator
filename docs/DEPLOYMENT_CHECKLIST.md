# Career Navigator — Deployment Checklist

Use this checklist before every production deployment.
**All items must be checked** before flipping traffic to a new release.

---

## Pre-Deployment (Day before)

### Code
- [ ] All unit tests pass: `make test-unit`
- [ ] All integration tests pass: `make test-integration`
- [ ] Ruff lint clean: `make lint`
- [ ] Security scan clean: GitHub Actions `security.yml` workflow green
- [ ] PR reviewed and approved by at least 1 engineer
- [ ] No `TODO: fix before prod` or `HACK:` comments in changed files
- [ ] CHANGELOG updated

### Database
- [ ] Alembic migration generated: `make migrate-make MSG="describe change"`
- [ ] Migration tested locally: `make migrate`
- [ ] `alembic downgrade -1` tested (rollback path works)
- [ ] Backup taken of production DB: `./scripts/db_backup_restore.sh backup`
- [ ] Backup uploaded to S3 and verified: `./scripts/db_backup_restore.sh verify`

### Secrets / Config
- [ ] `.env.example` updated with any new env vars
- [ ] Production secrets updated in AWS Secrets Manager (not in code)
- [ ] `SECRET_KEY` is >= 32 hex chars (`make secret`)
- [ ] `POSTGRES_PASSWORD` is strong (not "postgres")
- [ ] API keys rotated if > 90 days old: ANTHROPIC, ADZUNA

### Infrastructure
- [ ] Docker images built and pushed to GHCR: `make build && docker push ...`
- [ ] New images scanned for CVEs (GitHub Actions CD workflow)
- [ ] Terraform plan reviewed: `cd terraform && terraform plan -var-file=prod.tfvars`
- [ ] No unexpected resource deletions in the plan

---

## Deployment Window

### T-30 minutes
- [ ] Notify team in Slack #deployments: "Deploying v{version} in 30 min"
- [ ] Confirm monitoring dashboards are open: Grafana + CloudWatch
- [ ] Set maintenance page in Nginx (optional for major releases)

### T-0: Deploy

```bash
# 1. Apply infrastructure changes (if any)
cd terraform && terraform apply -var-file=prod.tfvars

# 2. Run migrations (before rolling restart)
aws ecs run-task \
  --cluster career-navigator-prod-cluster \
  --task-definition career-navigator-prod-api \
  --overrides '{"containerOverrides":[{"name":"api","command":["alembic","upgrade","head"]}]}'

# 3. Rolling restart (worker first, then API)
aws ecs update-service --cluster career-navigator-prod-cluster \
  --service career-navigator-prod-worker \
  --force-new-deployment

aws ecs update-service --cluster career-navigator-prod-cluster \
  --service career-navigator-prod-api \
  --force-new-deployment

# 4. Watch rollout
aws ecs wait services-stable \
  --cluster career-navigator-prod-cluster \
  --services career-navigator-prod-api career-navigator-prod-worker
```

### T+5: Smoke Tests

```bash
# Health check
curl -f https://careernavigator.ai/health
# Expected: {"status":"ok","version":"..."}

# FAIR calculator (no auth)
curl -f -X POST https://careernavigator.ai/api/resilience/fair-calc \
  -H "Content-Type: application/json" \
  -d '{"tef":4.0,"vulnerability":0.45,"primary_loss":50000}'
# Expected: {"ale": ..., "risk_level": "..."}

# Proctor catalog (no auth)
curl -f https://careernavigator.ai/api/proctor/catalog
# Expected: list of certs

# Metrics endpoint
curl -f http://internal-alb/metrics | grep http_requests_total
# Expected: Prometheus metric output
```

---

## Post-Deployment

### Verification (T+15 minutes)
- [ ] Error rate < 0.1% in Grafana for 15 minutes
- [ ] p95 latency within SLA for all endpoints
- [ ] No CRITICAL alerts fired in Prometheus Alertmanager
- [ ] Celery workers processing tasks (Flower dashboard)
- [ ] DB connections stable (< 15/20)
- [ ] At least 1 end-to-end user flow tested manually

### Monitoring window (T+1 hour)
- [ ] No memory leaks (RAM stable, not growing)
- [ ] No connection pool exhaustion
- [ ] Artifact generation working (test one inline artifact)

---

## Rollback Procedure

If any post-deployment check fails:

```bash
# Option 1: Force previous ECS task definition
PREV_REVISION=$(aws ecs describe-services \
  --cluster career-navigator-prod-cluster \
  --services career-navigator-prod-api \
  --query 'services[0].taskDefinition' --output text)

# Rollback to N-1 revision
aws ecs update-service \
  --cluster career-navigator-prod-cluster \
  --service career-navigator-prod-api \
  --task-definition career-navigator-prod-api:$((${PREV_REVISION##*:} - 1))

# Option 2: Restore database (if migration caused data corruption)
./scripts/db_backup_restore.sh restore backups/career_navigator_YYYYMMDD_HHMMSS.sql.gz
alembic downgrade -1
```

**Rollback decision time: < 15 minutes** from first sign of degradation.

---

## Escalation Contacts

| Issue | Owner | Contact |
|-------|-------|---------|
| Database down | DJ Jha | Slack @dj |
| API service down | DJ Jha | PagerDuty on-call |
| Payment / billing issue | DJ Jha | Stripe dashboard |
| AWS account issue | DJ Jha | AWS Support |
