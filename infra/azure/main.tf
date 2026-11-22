terraform {
  required_version = ">= 1.6.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
  }
}

provider "azurerm" {
  features {}
}

resource "azurerm_resource_group" "fleetflow" {
  name     = var.resource_group_name
  location = var.location
  tags     = local.tags
}

locals {
  tags = {
    project     = "FleetFlow"
    environment = "portfolio-review"
    managed_by  = "terraform"
  }
}

# Minimal Azure data-lake storage foundation. This is NOT wired to
# Databricks Free Edition, which has its own managed workspace.
resource "azurerm_storage_account" "lake" {
  name                            = var.storage_account_name
  resource_group_name             = azurerm_resource_group.fleetflow.name
  location                        = azurerm_resource_group.fleetflow.location
  account_tier                    = "Standard"
  account_replication_type        = "LRS"
  min_tls_version                 = "TLS1_2"
  https_traffic_only_enabled      = true
  allow_nested_items_to_be_public = false
  public_network_access_enabled   = false
  shared_access_key_enabled       = false
  is_hns_enabled                  = true
  tags                            = local.tags
}

# API deploy is intentionally opt-in. Existing backend needs an actual
# database, broker, container image and securely managed credentials.
resource "azurerm_log_analytics_workspace" "api" {
  count               = var.deploy_api ? 1 : 0
  name                = "${var.project_prefix}-logs"
  resource_group_name = azurerm_resource_group.fleetflow.name
  location            = azurerm_resource_group.fleetflow.location
  sku                 = "PerGB2018"
  retention_in_days   = 30
  tags                = local.tags
}

resource "azurerm_container_app_environment" "api" {
  count                      = var.deploy_api ? 1 : 0
  name                       = "${var.project_prefix}-env"
  resource_group_name        = azurerm_resource_group.fleetflow.name
  location                   = azurerm_resource_group.fleetflow.location
  log_analytics_workspace_id = azurerm_log_analytics_workspace.api[0].id
  tags                       = local.tags
}

resource "azurerm_container_app" "api" {
  count                        = var.deploy_api ? 1 : 0
  name                         = "${var.project_prefix}-api"
  resource_group_name          = azurerm_resource_group.fleetflow.name
  container_app_environment_id = azurerm_container_app_environment.api[0].id
  revision_mode                = "Single"
  tags                         = local.tags

  lifecycle {
    precondition {
      condition     = length(var.api_image) > 0 && length(var.database_url) > 0 && length(var.jwt_secret_key) >= 32 && length(var.kafka_bootstrap_servers) > 0
      error_message = "API opt-in requires a real image, database URL, Kafka bootstrap and strong JWT key; no fixture defaults."
    }
  }

  secret {
    name  = "database-url"
    value = var.database_url
  }

  secret {
    name  = "jwt-secret"
    value = var.jwt_secret_key
  }

  template {
    min_replicas = 0
    max_replicas = 1

    container {
      name   = "fleetflow-api"
      image  = var.api_image
      cpu    = 0.5
      memory = "1Gi"

      env {
        name        = "DATABASE_URL"
        secret_name = "database-url"
      }
      env {
        name        = "JWT_SECRET_KEY"
        secret_name = "jwt-secret"
      }
      env {
        name  = "KAFKA_BOOTSTRAP_SERVERS"
        value = var.kafka_bootstrap_servers
      }
      env {
        name  = "ENVIRONMENT"
        value = "production"
      }
    }
  }

  ingress {
    external_enabled = var.public_api_ingress
    target_port      = 8000
    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }
}
