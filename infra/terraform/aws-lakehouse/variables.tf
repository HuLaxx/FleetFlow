variable "aws_account_id" {
  description = "Explicit 12-digit AWS account ID; fails closed on wrong account."
  type        = string
  validation {
    condition     = can(regex("^[0-9]{12}$", var.aws_account_id))
    error_message = "Provide a real twelve-digit account ID after owner review."
  }
}

variable "aws_region" {
  description = "AWS region of any future reviewed deployment."
  type        = string
  default     = "eu-west-2"
  validation {
    condition     = can(regex("^[a-z]{2}(-gov)?-[a-z]+-[0-9]+$", var.aws_region))
    error_message = "Specify a valid AWS region name."
  }
}

variable "resource_prefix" {
  description = "Lowercase, short, unique resource prefix."
  type        = string
  default     = "fleetflow-review"
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{2,20}$", var.resource_prefix))
    error_message = "Use 3-21 lowercase letters, numbers or dashes; start with a letter."
  }
}

variable "owner_approved" {
  description = "Must be explicitly set after human cost/security review. False blocks any real plan/apply."
  type        = bool
  default     = false
}

variable "raw_retention_days" {
  description = "Expire raw telemetry objects and GPS payloads; not a live legal/privacy policy."
  type        = number
  default     = 7
  validation {
    condition     = var.raw_retention_days >= 1 && var.raw_retention_days <= 30
    error_message = "Raw GPS retention must be between 1 and 30 days."
  }
}

variable "clean_retention_days" {
  type    = number
  default = 30
  validation {
    condition     = var.clean_retention_days >= 1 && var.clean_retention_days <= 90
    error_message = "Clean GPS retention must be between 1 and 90 days."
  }
}

variable "curated_retention_days" {
  type    = number
  default = 90
  validation {
    condition     = var.curated_retention_days >= 1 && var.curated_retention_days <= 365
    error_message = "Curated data retention must be between 1 and 365 days."
  }
}

variable "athena_scan_bytes_per_query" {
  description = "Single-query Athena workgroup scan limit, not a monthly billing cap."
  type        = number
  default     = 1073741824
  validation {
    condition     = var.athena_scan_bytes_per_query >= 10485760 && var.athena_scan_bytes_per_query <= 5368709120
    error_message = "Limit each Athena query to between 10 MB and 5 GB scanned."
  }
}

variable "enable_budget_alert" {
  description = "Optional account-level AWS budget alert. Alert does NOT prevent charges."
  type        = bool
  default     = false
}

variable "budget_alert_email" {
  description = "Email for optional actual-spend budget notice; do not commit personal addresses."
  type        = string
  default     = ""
  validation {
    condition     = !var.enable_budget_alert || can(regex("^[^@ ]+@[^@ ]+\\.[^@ ]+$", var.budget_alert_email))
    error_message = "Budget alert enabled: supply a valid notification email privately."
  }
}

variable "enable_github_oidc_audit_role" {
  description = "Only if the AWS account already has GitHub token.actions.githubusercontent.com OIDC configured."
  type        = bool
  default     = false
}
