variable "project_name" {
  description = "Nom du projet, utilisé pour nommer les ressources."
  type        = string
}

variable "resource_group_name" {
  description = "Nom du groupe de ressources."
  type        = string
}

variable "location" {
  description = "Région Azure où déployer les ressources."
  type        = string
}

variable "common_tags" {
  description = "Tags communs à appliquer à toutes les ressources pour l'organisation et le suivi des coûts."
  type        = map(string)
  default     = {}
}
