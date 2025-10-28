

# 📂 RESOURCE GROUP
variable "resource_group_name" {
  description = "Logical container for all pipeline resources"
  default     = "RG_DBREAU"
}

# 📍 LOCATION
variable "location" {
  description = "Datacenter geolocation for latency optimization"
  default     = "francecentral"
}

# 🏷️ PROJECT
variable "project_name" {
  description = "Naming prefix for resource identification"
  default     = "water_quality"
}

# 🌊 DATA LAKE
variable "lake_name" {
  description = "Globally unique storage account identifier"
  default     = "adls4waterquality"
}

# 🧱 DATABRICKS
variable "databricks_workspace_name" {
  description = "Spark cluster workspace for data processing"
  default     = "dbw-water-quality-france"
}

# 🔖 TAGS
variable "common_tags" {
  description = "Resource metadata for cost tracking and governance"
  type        = map(string)
  default = {
    project   = "Water Quality France"
    env       = "prod"
    managedBy = "Terraform"
    source    = "data.gouv.fr"
  }
}

