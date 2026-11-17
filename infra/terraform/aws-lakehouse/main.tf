locals {
  lake_bucket_name    = "${var.resource_prefix}-${var.aws_account_id}-${var.aws_region}-lake"
  results_bucket_name = "${var.resource_prefix}-${var.aws_account_id}-${var.aws_region}-athena"
  catalog_name        = replace("${var.resource_prefix}_analytics", "-", "_")
}

resource "aws_s3_bucket" "lake" {
  bucket        = local.lake_bucket_name
  force_destroy = false # Teardown requires explicit review + bucket emptying.
  lifecycle {
    precondition {
      condition     = var.owner_approved
      error_message = "Owner sign-off required: set owner_approved=true only after cost/security review."
    }
  }
}

resource "aws_s3_bucket_public_access_block" "lake" {
  bucket                  = aws_s3_bucket.lake.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_ownership_controls" "lake" {
  bucket = aws_s3_bucket.lake.id
  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "lake" {
  bucket = aws_s3_bucket.lake.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_versioning" "lake" {
  bucket = aws_s3_bucket.lake.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "lake" {
  bucket = aws_s3_bucket.lake.id

  rule {
    id     = "raw-gps-expiry"
    status = "Enabled"
    filter {
      prefix = "raw/"
    }
    expiration {
      days = var.raw_retention_days
    }
    noncurrent_version_expiration {
      noncurrent_days = 7
    }
    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }

  rule {
    id     = "clean-gps-expiry"
    status = "Enabled"
    filter {
      prefix = "clean/"
    }
    expiration {
      days = var.clean_retention_days
    }
    noncurrent_version_expiration {
      noncurrent_days = 7
    }
  }

  rule {
    id     = "curated-gps-expiry"
    status = "Enabled"
    filter {
      prefix = "curated/"
    }
    expiration {
      days = var.curated_retention_days
    }
    noncurrent_version_expiration {
      noncurrent_days = 7
    }
  }
}

resource "aws_s3_bucket" "query_results" {
  bucket        = local.results_bucket_name
  force_destroy = false
}

resource "aws_s3_bucket_public_access_block" "query_results" {
  bucket                  = aws_s3_bucket.query_results.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_ownership_controls" "query_results" {
  bucket = aws_s3_bucket.query_results.id
  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "query_results" {
  bucket = aws_s3_bucket.query_results.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "query_results" {
  bucket = aws_s3_bucket.query_results.id
  rule {
    id     = "expire-query-results"
    status = "Enabled"
    filter {
      prefix = "results/"
    }
    expiration {
      days = 7
    }
  }
}

data "aws_iam_policy_document" "require_tls" {
  statement {
    sid     = "DenyInsecureTransport"
    effect  = "Deny"
    actions = ["s3:*"]
    resources = [
      aws_s3_bucket.lake.arn,
      "${aws_s3_bucket.lake.arn}/*",
    ]
    principals {
      type        = "*"
      identifiers = ["*"]
    }
    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
  }
}

resource "aws_s3_bucket_policy" "lake_tls" {
  bucket = aws_s3_bucket.lake.id
  policy = data.aws_iam_policy_document.require_tls.json
  depends_on = [
    aws_s3_bucket_public_access_block.lake,
  ]
}

resource "aws_glue_catalog_database" "analytics" {
  name        = local.catalog_name
  description = "Catalog namespace only; does not create ETL jobs, crawlers or tables"
}

resource "aws_athena_workgroup" "review" {
  name          = "${var.resource_prefix}-review"
  state         = "ENABLED"
  force_destroy = false
  configuration {
    enforce_workgroup_configuration    = true
    publish_cloudwatch_metrics_enabled = true
    bytes_scanned_cutoff_per_query     = var.athena_scan_bytes_per_query
    result_configuration {
      output_location = "s3://${aws_s3_bucket.query_results.id}/results/"
      encryption_configuration {
        encryption_option = "SSE_S3"
      }
    }
  }
}

# This creates a log group but does NOT connect an actual application logger.
resource "aws_cloudwatch_log_group" "review" {
  name              = "/fleetflow/${var.resource_prefix}/review"
  retention_in_days = 7
}

# Explicit opt-in, optionally creates an AWS Budgets alert at 80% of $5/month.
# AWS Budget alerts are NOT hard spending caps, may be delayed and can have fees.
resource "aws_budgets_budget" "monthly" {
  count        = var.enable_budget_alert ? 1 : 0
  name         = "${var.resource_prefix}-monthly-cost"
  budget_type  = "COST"
  limit_amount = "5"
  limit_unit   = "USD"
  time_unit    = "MONTHLY"
  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 80
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = [var.budget_alert_email]
  }
}
