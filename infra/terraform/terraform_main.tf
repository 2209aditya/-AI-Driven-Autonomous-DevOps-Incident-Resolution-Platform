# infra/terraform/main.tf
terraform {
  required_version = ">= 1.5.0"
  
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
  }
  
  backend "azurerm" {
    resource_group_name  = "tfstate-rg"
    storage_account_name = "tfstateaiops"
    container_name       = "tfstate"
    key                  = "aiops.terraform.tfstate"
  }
}

provider "azurerm" {
  features {}
}

# Resource Group
resource "azurerm_resource_group" "aiops" {
  name     = var.resource_group_name
  location = var.location
  
  tags = {
    Environment = var.environment
    ManagedBy   = "Terraform"
    Project     = "AI-DevOps"
  }
}

# Azure Kubernetes Service (AKS)
resource "azurerm_kubernetes_cluster" "main" {
  name                = "${var.prefix}-aks"
  location            = azurerm_resource_group.aiops.location
  resource_group_name = azurerm_resource_group.aiops.name
  dns_prefix          = "${var.prefix}-aks"
  kubernetes_version  = var.kubernetes_version

  default_node_pool {
    name                = "system"
    node_count          = var.system_node_count
    vm_size             = var.system_node_size
    os_disk_size_gb     = 128
    vnet_subnet_id      = azurerm_subnet.aks.id
    enable_auto_scaling = true
    min_count           = 2
    max_count           = 5
    
    node_labels = {
      "nodepool-type" = "system"
      "environment"   = var.environment
    }
  }

  identity {
    type = "SystemAssigned"
  }

  network_profile {
    network_plugin    = "azure"
    network_policy    = "calico"
    load_balancer_sku = "standard"
    service_cidr      = "10.0.16.0/22"
    dns_service_ip    = "10.0.16.10"
  }

  # Enable monitoring
  oms_agent {
    log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id
  }

  tags = {
    Environment = var.environment
  }
}

# Application Node Pool (for workloads)
resource "azurerm_kubernetes_cluster_node_pool" "apps" {
  name                  = "apps"
  kubernetes_cluster_id = azurerm_kubernetes_cluster.main.id
  vm_size               = var.app_node_size
  node_count            = var.app_node_count
  enable_auto_scaling   = true
  min_count             = 3
  max_count             = 10
  
  node_labels = {
    "nodepool-type" = "applications"
    "workload"      = "general"
  }
  
  node_taints = []
}

# AI/ML Node Pool (GPU nodes for ML workloads)
resource "azurerm_kubernetes_cluster_node_pool" "ml" {
  name                  = "ml"
  kubernetes_cluster_id = azurerm_kubernetes_cluster.main.id
  vm_size               = "Standard_NC6s_v3"  # GPU node
  node_count            = 1
  enable_auto_scaling   = true
  min_count             = 1
  max_count             = 3
  
  node_labels = {
    "nodepool-type" = "ml"
    "workload"      = "ai-ml"
  }
  
  node_taints = [
    "workload=ml:NoSchedule"
  ]
}

# Virtual Network
resource "azurerm_virtual_network" "main" {
  name                = "${var.prefix}-vnet"
  location            = azurerm_resource_group.aiops.location
  resource_group_name = azurerm_resource_group.aiops.name
  address_space       = ["10.0.0.0/16"]
}

resource "azurerm_subnet" "aks" {
  name                 = "aks-subnet"
  resource_group_name  = azurerm_resource_group.aiops.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.0.0.0/20"]
}

# Log Analytics Workspace (for Azure Monitor)
resource "azurerm_log_analytics_workspace" "main" {
  name                = "${var.prefix}-logs"
  location            = azurerm_resource_group.aiops.location
  resource_group_name = azurerm_resource_group.aiops.name
  sku                 = "PerGB2018"
  retention_in_days   = 30
}

# Application Insights
resource "azurerm_application_insights" "main" {
  name                = "${var.prefix}-appinsights"
  location            = azurerm_resource_group.aiops.location
  resource_group_name = azurerm_resource_group.aiops.name
  workspace_id        = azurerm_log_analytics_workspace.main.id
  application_type    = "web"
}

# Azure OpenAI (for GenAI)
resource "azurerm_cognitive_account" "openai" {
  name                = "${var.prefix}-openai"
  location            = "eastus"  # OpenAI is region-specific
  resource_group_name = azurerm_resource_group.aiops.name
  kind                = "OpenAI"
  sku_name            = "S0"
  
  custom_subdomain_name = "${var.prefix}-openai"
}

resource "azurerm_cognitive_deployment" "gpt4" {
  name                 = "gpt-4"
  cognitive_account_id = azurerm_cognitive_account.openai.id
  
  model {
    format  = "OpenAI"
    name    = "gpt-4"
    version = "0613"
  }
  
  scale {
    type     = "Standard"
    capacity = 10
  }
}

# Azure Container Registry (for Docker images)
resource "azurerm_container_registry" "main" {
  name                = "${var.prefix}acr"
  resource_group_name = azurerm_resource_group.aiops.name
  location            = azurerm_resource_group.aiops.location
  sku                 = "Premium"
  admin_enabled       = false
  
  georeplications {
    location = "westus2"
    tags     = {}
  }
}

# Grant AKS access to ACR
resource "azurerm_role_assignment" "aks_acr" {
  principal_id                     = azurerm_kubernetes_cluster.main.kubelet_identity[0].object_id
  role_definition_name             = "AcrPull"
  scope                            = azurerm_container_registry.main.id
  skip_service_principal_aad_check = true
}

# Azure Database for PostgreSQL (for incident history)
resource "azurerm_postgresql_flexible_server" "main" {
  name                   = "${var.prefix}-postgres"
  resource_group_name    = azurerm_resource_group.aiops.name
  location               = azurerm_resource_group.aiops.location
  version                = "14"
  administrator_login    = var.db_admin_username
  administrator_password = var.db_admin_password
  storage_mb             = 32768
  sku_name               = "GP_Standard_D2s_v3"
  zone                   = "1"
  
  high_availability {
    mode = "ZoneRedundant"
  }
}

resource "azurerm_postgresql_flexible_server_database" "aiops" {
  name      = "aiops"
  server_id = azurerm_postgresql_flexible_server.main.id
  charset   = "UTF8"
  collation = "en_US.utf8"
}

# Azure Redis Cache (for caching and pub/sub)
resource "azurerm_redis_cache" "main" {
  name                = "${var.prefix}-redis"
  location            = azurerm_resource_group.aiops.location
  resource_group_name = azurerm_resource_group.aiops.name
  capacity            = 2
  family              = "C"
  sku_name            = "Standard"
  enable_non_ssl_port = false
  minimum_tls_version = "1.2"

  redis_configuration {
    maxmemory_reserved = 50
    maxmemory_delta    = 50
    maxmemory_policy   = "allkeys-lru"
  }
}

# Outputs
output "kube_config" {
  value     = azurerm_kubernetes_cluster.main.kube_config_raw
  sensitive = true
}

output "openai_endpoint" {
  value = azurerm_cognitive_account.openai.endpoint
}

output "openai_key" {
  value     = azurerm_cognitive_account.openai.primary_access_key
  sensitive = true
}

output "acr_login_server" {
  value = azurerm_container_registry.main.login_server
}

output "postgres_fqdn" {
  value = azurerm_postgresql_flexible_server.main.fqdn
}

output "redis_hostname" {
  value = azurerm_redis_cache.main.hostname
}