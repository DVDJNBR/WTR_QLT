# ===================================================================
# 📊 Water Quality Pipeline - Terraform Outputs
# ===================================================================

# 🌊 DATA LAKE OUTPUTS
output "datalake_name" {
  description = "Data Lake Storage account name"
  value       = azurerm_storage_account.datalake.name
}

output "datalake_primary_endpoint" {
  description = "Data Lake primary endpoint URL"
  value       = azurerm_storage_account.datalake.primary_dfs_endpoint
}

output "datalake_primary_access_key" {
  description = "Data Lake primary access key"
  value       = azurerm_storage_account.datalake.primary_access_key
  sensitive   = true
}

output "datalake_connection_string" {
  description = "Data Lake connection string"
  value       = azurerm_storage_account.datalake.primary_connection_string
  sensitive   = true
}

# 🧱 DATABRICKS OUTPUTS
output "databricks_workspace_url" {
  description = "Databricks workspace URL"
  value       = "https://${azurerm_databricks_workspace.main.workspace_url}"
}

output "databricks_workspace_id" {
  description = "Databricks workspace ID"
  value       = azurerm_databricks_workspace.main.workspace_id
}

# 📦 RESOURCE GROUP OUTPUTS
output "resource_group_name" {
  description = "Resource group name"
  value       = data.azurerm_resource_group.main.name
}

output "resource_group_location" {
  description = "Resource group location"
  value       = data.azurerm_resource_group.main.location
}

# 🔐 SUBSCRIPTION OUTPUT
output "subscription_id" {
  description = "Azure subscription ID"
  value       = data.azurerm_client_config.current.subscription_id
  sensitive   = true
}

# 📦 CONTAINERS OUTPUTS
output "containers" {
  description = "Data Lake containers created"
  value = {
    bronze   = azurerm_storage_data_lake_gen2_filesystem.bronze.name
    silver   = azurerm_storage_data_lake_gen2_filesystem.silver.name
    gold     = azurerm_storage_data_lake_gen2_filesystem.gold.name
    raw_data = azurerm_storage_data_lake_gen2_filesystem.raw_data.name
  }
}