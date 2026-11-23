terraform {
  required_version = ">= 1.6.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.110"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  # Remote state is configured at init time, e.g.
  #   terraform init -backend-config="storage_account_name=..." -backend-config="container_name=tfstate"
  backend "azurerm" {}
}

provider "azurerm" {
  # The lake disables shared keys, so data-plane calls (creating containers) use Entra ID.
  storage_use_azuread = true

  features {
    key_vault {
      purge_soft_delete_on_destroy = false
    }
  }
}
