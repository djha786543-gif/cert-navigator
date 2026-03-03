# Terraform outputs — Career Navigator AWS

output "alb_dns_name" {
  description = "ALB DNS name — point your CNAME here"
  value       = aws_lb.main.dns_name
}

output "api_url" {
  description = "API base URL (via ALB)"
  value       = "http://${aws_lb.main.dns_name}"
}

output "rds_endpoint" {
  description = "RDS PostgreSQL endpoint (private — not publicly accessible)"
  value       = aws_db_instance.main.address
  sensitive   = true
}

output "redis_endpoint" {
  description = "ElastiCache Redis primary endpoint"
  value       = aws_elasticache_replication_group.main.primary_endpoint_address
  sensitive   = true
}

output "artifacts_bucket" {
  description = "S3 bucket name for artifact storage"
  value       = aws_s3_bucket.artifacts.bucket
}

output "ecs_cluster_name" {
  description = "ECS cluster name — for 'aws ecs' CLI commands"
  value       = aws_ecs_cluster.main.name
}

output "secrets_arn" {
  description = "Secrets Manager ARN containing all app secrets"
  value       = aws_secretsmanager_secret.app_secrets.arn
}

output "cloudwatch_log_groups" {
  description = "CloudWatch log group names"
  value = {
    api    = aws_cloudwatch_log_group.api.name
    worker = aws_cloudwatch_log_group.worker.name
  }
}

output "next_steps" {
  description = "Post-deployment checklist"
  value       = <<-EOT
    ==========================================================
    Career Navigator deployed successfully!

    Next steps:
    1. Run Alembic migrations:
         aws ecs run-task \
           --cluster ${aws_ecs_cluster.main.name} \
           --task-definition ${aws_ecs_task_definition.api.family} \
           --overrides '{"containerOverrides":[{"name":"api","command":["alembic","upgrade","head"]}]}'

    2. Point DNS:
         CNAME careernavigator.ai → ${aws_lb.main.dns_name}

    3. Verify health:
         curl http://${aws_lb.main.dns_name}/health

    4. View logs:
         aws logs tail ${aws_cloudwatch_log_group.api.name} --follow

    5. Run load test:
         locust -f tests/load/locustfile.py \
                --host=http://${aws_lb.main.dns_name} \
                --users=50 --spawn-rate=5 --run-time=5m --headless
    ==========================================================
  EOT
}
