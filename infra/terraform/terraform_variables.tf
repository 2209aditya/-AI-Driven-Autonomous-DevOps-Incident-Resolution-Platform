# infra/terraform/variables.tf

variable "prefix" {
  description = "Prefix for all resources"
  type        = string
  default     = "aiops"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

variable "location" {
  description = "Azure region"
  type        = string
  default     = "eastus"
}

variable "resource_group_name" {
  description = "Resource group name"
  type        = string
  default     = "aiops-rg"
}

variable "kubernetes_version" {
  description = "Kubernetes version"
  type        = string
  default     = "1.28"
}

variable "system_node_count" {
  description = "Number of system nodes"
  type        = number
  default     = 3
}

variable "system_node_size" {
  description = "VM size for system nodes"
  type        = string
  default     = "Standard_D4s_v3"
}

variable "app_node_count" {
  description = "Number of application nodes"
  type        = number
  default     = 5
}

variable "app_node_size" {
  description = "VM size for application nodes"
  type        = string
  default     = "Standard_D8s_v3"
}

variable "db_admin_username" {
  description = "PostgreSQL admin username"
  type        = string
  sensitive   = true
}

variable "db_admin_password" {
  description = "PostgreSQL admin password"
  type        = string
  sensitive   = true
}