terraform {
  required_version = ">= 1.7.0, < 2.0.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

# No state backend is configured in this review-only module.
# Before any real apply, provision a separate audited remote state backend
# with encryption, locking and limited read/write access.
provider "aws" {
  region              = var.aws_region
  allowed_account_ids = [var.aws_account_id]
  default_tags {
    tags = {
      Project     = "FleetFlow"
      Environment = "review"
      ManagedBy   = "terraform"
      Owner       = "HuLaX"
    }
  }
}
