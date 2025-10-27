# ===================================================================
# 🌊 Water Quality Pipeline - Azure Infrastructure
# ===================================================================

terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~>3.0"
    }
  }
}

provider "azurerm" {
  features {}
  # subscription_id auto-detected from az cli context
}

# Get current Azure client config
data "azurerm_client_config" "current" {}

# 📂 RESOURCE GROUP (existing)
data "azurerm_resource_group" "main" {
  name = var.resource_group_name
}

# 🌊 DATA LAKE STORAGE GEN2
resource "azurerm_storage_account" "datalake" {
  name                     = var.lake_name
  resource_group_name      = data.azurerm_resource_group.main.name
  location                 = data.azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  account_kind             = "StorageV2"
  is_hns_enabled           = true  # Hierarchical namespace for Data Lake Gen2

  tags = var.common_tags
}

# 📦 CONTAINERS (Bronze, Silver, Gold)
resource "azurerm_storage_data_lake_gen2_filesystem" "bronze" {
  name               = "bronze"
  storage_account_id = azurerm_storage_account.datalake.id
}

resource "azurerm_storage_data_lake_gen2_filesystem" "silver" {
  name               = "silver"
  storage_account_id = azurerm_storage_account.datalake.id
}

resource "azurerm_storage_data_lake_gen2_filesystem" "gold" {
  name               = "gold"
  storage_account_id = azurerm_storage_account.datalake.id
}

resource "azurerm_storage_data_lake_gen2_filesystem" "raw_data" {
  name               = "raw-data"
  storage_account_id = azurerm_storage_account.datalake.id
}

# 🧱 DATABRICKS WORKSPACE
resource "azurerm_databricks_workspace" "main" {
  name                = var.databricks_workspace_name
  resource_group_name = data.azurerm_resource_group.main.name
  location            = data.azurerm_resource_group.main.location
  sku                 = "standard"  # standard = moins cher que premium

  # Optimisations coût
  public_network_access_enabled = true

  tags = var.common_tags
}