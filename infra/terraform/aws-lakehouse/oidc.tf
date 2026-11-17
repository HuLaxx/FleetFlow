# Opt-in, read-only GitHub audit role; never allows terraform apply.
# Requires a PRE-EXISTING AWS GitHub Actions OIDC provider, which this module
# deliberately does not create/modify. No wildcard refs or PR trust.
resource "aws_iam_role" "github_audit" {
  count = var.enable_github_oidc_audit_role ? 1 : 0
  name  = "${var.resource_prefix}-github-audit"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Federated = "arn:aws:iam::${var.aws_account_id}:oidc-provider/token.actions.githubusercontent.com"
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
            "token.actions.githubusercontent.com:sub" = "repo:HuLaxx/FleetFlow:ref:refs/heads/main"
          }
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "github_audit" {
  count = var.enable_github_oidc_audit_role ? 1 : 0
  role  = aws_iam_role.github_audit[0].id
  name  = "${var.resource_prefix}-github-audit-read-only"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "ReadOnlyLakeMetadata"
        Effect   = "Allow"
        Action   = [
          "s3:GetBucketLocation",
          "s3:GetBucketPolicy",
          "s3:GetBucketPublicAccessBlock",
          "s3:GetBucketVersioning",
          "s3:GetEncryptionConfiguration",
          "s3:GetLifecycleConfiguration",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.lake.arn,
          aws_s3_bucket.query_results.arn
        ]
      },
      {
        Sid    = "ReadOnlyServiceMetadata"
        Effect = "Allow"
        Action = [
          "glue:GetDatabase",
          "athena:GetWorkGroup",
          "logs:DescribeLogGroups"
        ]
        Resource = "*"
      }
    ]
  })
}
