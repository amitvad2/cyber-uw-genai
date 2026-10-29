terraform {
  required_version = ">= 1.5"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }
  # Bootstrap uses LOCAL state (it creates the remote state bucket the main stack uses).
}

provider "google" {
  project = var.project_id
  region  = var.region
}
