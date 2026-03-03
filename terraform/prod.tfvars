# Production environment values
# Secrets (secret_key, db_password, anthropic_api_key, adzuna_app_key)
# must be set via environment variables:
#   export TF_VAR_secret_key=$(python -c "import secrets; print(secrets.token_hex(32))")
#   export TF_VAR_db_password="<strong-password>"
#   export TF_VAR_anthropic_api_key="<your-key>"
#   export TF_VAR_adzuna_app_key="<your-key>"

aws_region  = "us-west-2"
environment = "prod"
app_name    = "career-navigator"

# Images — update after GitHub Actions CD pushes to GHCR
api_image      = "ghcr.io/your-org/career-navigator-api:latest"
frontend_image = "ghcr.io/your-org/career-navigator-frontend:latest"

# ECS sizing (50 users)
api_cpu          = 512    # 0.5 vCPU
api_memory       = 2048   # 2 GB
api_desired_count = 2
worker_cpu       = 1024   # 1 vCPU
worker_memory    = 4096   # 4 GB

# RDS
rds_instance_class        = "db.t4g.medium"
rds_allocated_storage     = 50
rds_max_allocated_storage = 200
rds_engine_version        = "16.2"
db_name                   = "career_navigator"
db_username               = "postgres"

# ElastiCache
redis_node_type = "cache.t4g.small"

# Adzuna (non-sensitive)
adzuna_app_id = "your-adzuna-app-id"

# Domain (optional — set if you have a custom domain + ACM cert)
# domain_name     = "careernavigator.ai"
# certificate_arn = "arn:aws:acm:us-west-2:123456789012:certificate/..."
