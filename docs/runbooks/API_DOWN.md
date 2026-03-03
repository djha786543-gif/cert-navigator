# Runbook: API Down

**Alert:** `APIDown` — FastAPI unreachable for > 30 seconds
**Severity:** Critical
**Response time:** Immediate

---

## Symptoms
- `/health` returns connection refused or timeout
- ALB health checks failing (502 Bad Gateway to users)
- `up{job="career_api"} == 0` in Prometheus

## Diagnosis

```bash
# 1. Check ECS service status
aws ecs describe-services \
  --cluster career-navigator-prod-cluster \
  --services career-navigator-prod-api \
  --query 'services[0].{status:status,running:runningCount,desired:desiredCount,events:events[0:3]}'

# 2. Check recent logs
aws logs tail /ecs/career-navigator-prod-api --since 10m

# 3. Check stopped tasks
aws ecs list-tasks \
  --cluster career-navigator-prod-cluster \
  --service-name career-navigator-prod-api \
  --desired-status STOPPED \
  --query 'taskArns[0]'

aws ecs describe-tasks \
  --cluster career-navigator-prod-cluster \
  --tasks <task-arn> \
  --query 'tasks[0].stoppedReason'

# 4. Check DB connectivity (api depends on DB)
psql -h $DB_HOST -U postgres -d career_navigator -c "SELECT 1"
```

## Common Causes and Fixes

### OOM (Out of Memory)
```
Stopped reason: "OutOfMemoryError: Container killed due to memory usage"
```
Fix: Reduce `--workers` from 4 to 2, or increase task memory:
```bash
# docker-compose.yml — reduce embedding memory footprint
command: uvicorn backend.app.main:app --workers 2 ...

# Terraform — increase task memory
terraform apply -var="api_memory=4096"
```

### Database connection refused at startup
```
Stopped reason: "DB init failed: connection refused"
```
Fix: Ensure RDS is running and security groups allow ECS → RDS:
```bash
aws rds describe-db-instances --db-instance-identifier career-navigator-prod-postgres
```

### Missing environment variable
```
KeyError or ValidationError in config.py
```
Fix: Check all required env vars are in ECS task definition:
`SECRET_KEY`, `DATABASE_URL`, `REDIS_URL`, `CELERY_BROKER_URL`

### Bad Docker image (failed startup)
Fix: Roll back to previous task definition revision:
```bash
aws ecs update-service \
  --cluster career-navigator-prod-cluster \
  --service career-navigator-prod-api \
  --task-definition career-navigator-prod-api:<previous-revision>
```

## Recovery

```bash
# Force new deployment (restarts all tasks)
aws ecs update-service \
  --cluster career-navigator-prod-cluster \
  --service career-navigator-prod-api \
  --force-new-deployment

# Wait for stable
aws ecs wait services-stable \
  --cluster career-navigator-prod-cluster \
  --services career-navigator-prod-api

# Verify
curl https://careernavigator.ai/health
```

## Post-Incident

- [ ] Document root cause in `docs/incidents/YYYY-MM-DD.md`
- [ ] Add a test to catch the issue earlier
- [ ] Update this runbook if fix was different from above
