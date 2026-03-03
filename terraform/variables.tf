# Terraform variables — Career Navigator AWS deployment
# Override per environment via: terraform apply -var-file=prod.tfvars

variable "aws_region" {
  description = "AWS region to deploy into"
  type        = string
  default     = "us-west-2"
}

variable "environment" {
  description = "Deployment environment tag (dev | staging | prod)"
  type        = string
  default     = "prod"
}

variable "app_name" {
  description = "Application name — used as prefix for all resource names"
  type        = string
  default     = "career-navigator"
}

# ── Networking ─────────────────────────────────────────────────────────────

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for the two public subnets (ALB)"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for the two private subnets (ECS, RDS, Redis)"
  type        = list(string)
  default     = ["10.0.10.0/24", "10.0.11.0/24"]
}

# ── ECS ────────────────────────────────────────────────────────────────────

variable "api_image" {
  description = "Docker image URI for the FastAPI backend (e.g. ghcr.io/your-org/career-navigator-api:latest)"
  type        = string
}

variable "frontend_image" {
  description = "Docker image URI for the Next.js frontend"
  type        = string
}

variable "api_cpu" {
  description = "ECS task CPU units for the API (256 = 0.25 vCPU)"
  type        = number
  default     = 512   # 0.5 vCPU
}

variable "api_memory" {
  description = "ECS task memory (MB) for the API"
  type        = number
  default     = 2048  # 2 GB (embedding model needs ~600MB)
}

variable "api_desired_count" {
  description = "Number of API task replicas to run"
  type        = number
  default     = 2
}

variable "worker_cpu" {
  description = "ECS task CPU units for the Celery worker"
  type        = number
  default     = 1024  # 1 vCPU
}

variable "worker_memory" {
  description = "ECS task memory (MB) for the Celery worker"
  type        = number
  default     = 4096  # 4 GB (embedding + LLM inference)
}

# ── RDS ────────────────────────────────────────────────────────────────────

variable "rds_instance_class" {
  description = "RDS instance type"
  type        = string
  default     = "db.t4g.medium"  # 2 vCPU, 4GB — sufficient for 50 users
}

variable "rds_allocated_storage" {
  description = "RDS initial storage (GB)"
  type        = number
  default     = 50
}

variable "rds_max_allocated_storage" {
  description = "RDS storage autoscaling ceiling (GB)"
  type        = number
  default     = 200
}

variable "rds_engine_version" {
  description = "PostgreSQL engine version"
  type        = string
  default     = "16.2"
}

variable "db_name" {
  description = "PostgreSQL database name"
  type        = string
  default     = "career_navigator"
}

variable "db_username" {
  description = "PostgreSQL admin username"
  type        = string
  default     = "postgres"
  sensitive   = true
}

variable "db_password" {
  description = "PostgreSQL admin password — set via TF_VAR_db_password env var"
  type        = string
  sensitive   = true
}

# ── ElastiCache (Redis) ────────────────────────────────────────────────────

variable "redis_node_type" {
  description = "ElastiCache Redis node type"
  type        = string
  default     = "cache.t4g.small"  # 1.37 GB — fine for Celery queues
}

# ── S3 ──────────────────────────────────────────────────────────────────────

variable "artifacts_bucket_name" {
  description = "S3 bucket name for generated artifacts (study guides, exams)"
  type        = string
  default     = ""   # defaults to {app_name}-artifacts-{account_id}
}

# ── Secrets (passed from GitHub Actions / CI) ──────────────────────────────

variable "secret_key" {
  description = "JWT secret key — generate with: python -c \"import secrets; print(secrets.token_hex(32))\""
  type        = string
  sensitive   = true
}

variable "anthropic_api_key" {
  description = "Anthropic Claude API key"
  type        = string
  default     = ""
  sensitive   = true
}

variable "adzuna_app_id" {
  description = "Adzuna job search API app ID"
  type        = string
  default     = ""
}

variable "adzuna_app_key" {
  description = "Adzuna job search API key"
  type        = string
  default     = ""
  sensitive   = true
}

# ── Domain / SSL ──────────────────────────────────────────────────────────

variable "domain_name" {
  description = "Primary domain name (e.g. careernavigator.ai). Leave empty for ALB DNS only."
  type        = string
  default     = ""
}

variable "certificate_arn" {
  description = "ACM certificate ARN for HTTPS (required if domain_name is set)"
  type        = string
  default     = ""
}
