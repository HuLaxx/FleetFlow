locals {
  name = "${var.project}-${var.environment}"
  # Storage account names: 3-24 lowercase letters and digits, globally unique.
  sa_name = substr(replace("${var.project}${var.environment}lake${random_string.suffix.result}", "-", ""), 0, 24)
  layers  = ["bronze", "silver", "gold", "quarantine"]
  tags = merge({
    project     = var.project
    environment = var.environment
    managed_by  = "terraform"
  }, var.tags)
}

resource "random_string" "suffix" {
  length  = 5
  upper   = false
  special = false
}

data "azurerm_client_config" "current" {}

resource "azurerm_resource_group" "this" {
  name     = "rg-${local.name}"
  location = var.location
  tags     = local.tags
}

# ---- Data lake: ADLS Gen2 with one container per medallion layer -------------------
resource "azurerm_storage_account" "lake" {
  name                            = local.sa_name
  resource_group_name             = azurerm_resource_group.this.name
  location                        = azurerm_resource_group.this.location
  account_tier                    = "Standard"
  account_replication_type        = var.environment == "prod" ? "ZRS" : "LRS"
  account_kind                    = "StorageV2"
  is_hns_enabled                  = true # hierarchical namespace = ADLS Gen2
  min_tls_version                 = "TLS1_2"
  allow_nested_items_to_be_public = false
  shared_access_key_enabled       = false # force Entra ID (RBAC) access
  tags                            = local.tags

  blob_properties {
    delete_retention_policy {
      days = 7
    }
  }
}

resource "azurerm_storage_data_lake_gen2_filesystem" "layer" {
  for_each           = toset(local.layers)
  name               = each.value
  storage_account_id = azurerm_storage_account.lake.id
}

# Raw (bronze) files are cheap to keep but rarely read: move them to cool storage after 30 days.
resource "azurerm_storage_management_policy" "lake" {
  storage_account_id = azurerm_storage_account.lake.id

  rule {
    name    = "bronze-to-cool"
    enabled = true
    filters {
      prefix_match = ["bronze/"]
      blob_types   = ["blockBlob"]
    }
    actions {
      base_blob {
        tier_to_cool_after_days_since_modification_greater_than = 30
      }
    }
  }
}

# ---- Secrets ---------------------------------------------------------------------
resource "azurerm_key_vault" "this" {
  name                       = substr("kv-${replace(local.name, "-", "")}${random_string.suffix.result}", 0, 24)
  location                   = azurerm_resource_group.this.location
  resource_group_name        = azurerm_resource_group.this.name
  tenant_id                  = data.azurerm_client_config.current.tenant_id
  sku_name                   = "standard"
  enable_rbac_authorization  = true
  purge_protection_enabled   = var.environment == "prod"
  soft_delete_retention_days = 7
  tags                       = local.tags
}

# ---- Compute: Databricks workspace for the PySpark job ----------------------------
resource "azurerm_databricks_workspace" "this" {
  name                        = "dbw-${local.name}"
  resource_group_name         = azurerm_resource_group.this.name
  location                    = azurerm_resource_group.this.location
  sku                         = var.databricks_sku
  managed_resource_group_name = "rg-${local.name}-dbw-managed"
  tags                        = local.tags
}

# Databricks connects to the lake with its managed identity (no storage keys).
resource "azurerm_databricks_access_connector" "lake" {
  name                = "dbac-${local.name}"
  resource_group_name = azurerm_resource_group.this.name
  location            = azurerm_resource_group.this.location
  tags                = local.tags

  identity {
    type = "SystemAssigned"
  }
}

resource "azurerm_role_assignment" "databricks_lake" {
  scope                = azurerm_storage_account.lake.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_databricks_access_connector.lake.identity[0].principal_id
}

# ---- Observability ------------------------------------------------------------------
resource "azurerm_log_analytics_workspace" "this" {
  name                = "log-${local.name}"
  location            = azurerm_resource_group.this.location
  resource_group_name = azurerm_resource_group.this.name
  sku                 = "PerGB2018"
  retention_in_days   = 30
  tags                = local.tags
}

resource "azurerm_monitor_diagnostic_setting" "lake" {
  name                       = "lake-to-log-analytics"
  target_resource_id         = "${azurerm_storage_account.lake.id}/blobServices/default"
  log_analytics_workspace_id = azurerm_log_analytics_workspace.this.id

  enabled_log {
    category = "StorageWrite"
  }

  metric {
    category = "Transaction"
  }
}
