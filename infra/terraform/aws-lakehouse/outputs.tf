output "raw_clean_curated_bucket" {
  description = "Only S3 bucket name; no objects or telemetry uploaded"
  value       = aws_s3_bucket.lake.id
}

output "athena_results_bucket" {
  value = aws_s3_bucket.query_results.id
}

output "glue_catalog_database" {
  value = aws_glue_catalog_database.analytics.name
}

output "athena_workgroup" {
  value = aws_athena_workgroup.review.name
}

output "read_only_ci_role_arn" {
  description = "Only present if explicitly enabled and account OIDC provider exists"
  value       = var.enable_github_oidc_audit_role ? aws_iam_role.github_audit[0].arn : null
}
