output "resource_group" {
  value = azurerm_resource_group.this.name
}

output "lake_account" {
  value = azurerm_storage_account.lake.name
}

output "lake_paths" {
  description = "abfss:// URIs to pass to the Spark job (--root) per layer."
  value = {
    for layer in local.layers :
    layer => "abfss://${layer}@${azurerm_storage_account.lake.name}.dfs.core.windows.net/"
  }
}

output "databricks_workspace_url" {
  value = "https://${azurerm_databricks_workspace.this.workspace_url}"
}

output "databricks_access_connector_id" {
  value = azurerm_databricks_access_connector.lake.id
}
