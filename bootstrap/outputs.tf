output "tfstate_bucket" {
  value = google_storage_bucket.tfstate.name
}

output "wif_provider" {
  description = "Set as GitHub repo variable WIF_PROVIDER"
  value       = google_iam_workload_identity_pool_provider.github.name
}

output "ci_service_account" {
  description = "Set as GitHub repo variable CI_SERVICE_ACCOUNT"
  value       = google_service_account.ci.email
}

output "artifact_registry" {
  value = google_artifact_registry_repository.repo.id
}
