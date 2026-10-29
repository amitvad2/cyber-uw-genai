# One-time foundations that must exist BEFORE the main stack and the CI pipeline.

locals {
  bootstrap_apis = [
    "iam.googleapis.com",
    "iamcredentials.googleapis.com",
    "sts.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "serviceusage.googleapis.com",
    "artifactregistry.googleapis.com",
    "cloudbuild.googleapis.com",
  ]
}

resource "google_project_service" "bootstrap" {
  for_each           = toset(local.bootstrap_apis)
  service            = each.value
  disable_on_destroy = false
}

# --- Remote Terraform state bucket (used by ../terraform backend) ---
resource "google_storage_bucket" "tfstate" {
  name                        = "${var.project_id}-tfstate"
  location                    = var.region
  uniform_bucket_level_access = true
  force_destroy               = false
  versioning { enabled = true }
}

# --- Artifact Registry repo for the container image ---
resource "google_artifact_registry_repository" "repo" {
  repository_id = "uw-pipeline"
  location      = var.region
  format        = "DOCKER"
  description   = "Cyber UW pipeline service image"
  depends_on    = [google_project_service.bootstrap]
}

# --- CI service account used by GitHub Actions (via WIF, no keys) ---
resource "google_service_account" "ci" {
  account_id   = "uw-ci"
  display_name = "Cyber UW CI deployer"
}

# Roles CI needs to provision the main stack. Scoped to this demo project.
locals {
  ci_roles = [
    "roles/editor",
    "roles/resourcemanager.projectIamAdmin",
    "roles/iam.serviceAccountAdmin",
    "roles/iam.serviceAccountUser",
    "roles/run.admin",
    "roles/workflows.admin",
    "roles/eventarc.admin",
    "roles/artifactregistry.writer",
    "roles/cloudbuild.builds.editor",
  ]
}

resource "google_project_iam_member" "ci" {
  for_each = toset(local.ci_roles)
  project  = var.project_id
  role     = each.value
  member   = "serviceAccount:${google_service_account.ci.email}"
}

# --- Workload Identity Federation: let GitHub Actions impersonate the CI SA, keyless ---
resource "google_iam_workload_identity_pool" "github" {
  workload_identity_pool_id = "github-pool"
  display_name              = "GitHub Actions pool"
  depends_on                = [google_project_service.bootstrap]
}

resource "google_iam_workload_identity_pool_provider" "github" {
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = "github-provider"
  display_name                       = "GitHub OIDC"
  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.repository" = "assertion.repository"
  }
  attribute_condition = "assertion.repository == \"${var.github_repo}\""
  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

# Allow the specific repo's Actions runs to impersonate the CI SA
resource "google_service_account_iam_member" "wif_bind" {
  service_account_id = google_service_account.ci.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.repository/${var.github_repo}"
}
