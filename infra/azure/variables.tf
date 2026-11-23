variable "location" {
  description = "Azure region for the demo resources"
  type        = string
  default     = "uksouth"
}

variable "resource_group_name" {
  description = "Dedicated review resource group. Destroy only resources tracked by this state."
  type        = string
  default     = "rg-fleetflow-review"
}

variable "storage_account_name" {
  description = "Globally unique lowercase alphanumeric Azure storage account name"
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9]{3,24}$", var.storage_account_name))
    error_message = "Choose 3–24 lowercase letters or numbers."
  }
}

variable "project_prefix" {
  description = "Unique lowercase Azure Container Apps resource prefix"
  type        = string
  default     = "fleetflow-review"
}

variable "deploy_api" {
  description = "Default false: don't provision API, logs or Container App without backend dependencies"
  type        = bool
  default     = false
}

variable "api_image" {
  description = "Published container image with the actual FleetFlow backend, not a placeholder"
  type        = string
  default     = ""
}

variable "database_url" {
  description = "Real secured externally provisioned PostgreSQL/PostGIS URL; stored in Terraform state if used"
  type        = string
  default     = ""
  sensitive   = true
}

variable "jwt_secret_key" {
  description = "Strong randomly generated JWT secret; stored in Terraform state if used"
  type        = string
  default     = ""
  sensitive   = true
}

variable "kafka_bootstrap_servers" {
  description = "Reachable external Kafka-compatible broker; not provisioned by this module"
  type        = string
  default     = ""
}

variable "public_api_ingress" {
  description = "Default private. Public ingress only after explicit API security review"
  type        = bool
  default     = false
}
