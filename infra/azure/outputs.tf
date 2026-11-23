output "resource_group_name" {
  description = "Review-only resource group"
  value       = azurerm_resource_group.fleetflow.name
}

output "data_lake_storage_account" {
  description = "Private storage name; no Databricks connection is implied"
  value       = azurerm_storage_account.lake.name
}

output "api_fqdn" {
  description = "Only populated after approved, opt-in Container App provisioning"
  value       = var.deploy_api ? azurerm_container_app.api[0].latest_revision_fqdn : null
}
