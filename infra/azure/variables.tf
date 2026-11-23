variable "project" {
  description = "Short project name used in resource names."
  type        = string
  default     = "fleetflow"
}

variable "environment" {
  description = "Deployment environment."
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "environment must be one of dev, staging, prod."
  }
}

variable "location" {
  description = "Azure region."
  type        = string
  default     = "uksouth"
}

variable "databricks_sku" {
  description = "Databricks workspace tier. premium is required for Unity Catalog."
  type        = string
  default     = "premium"
}

variable "tags" {
  description = "Extra tags applied to every resource."
  type        = map(string)
  default     = {}
}
