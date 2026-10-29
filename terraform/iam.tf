# Runtime identity for all three Cloud Run services + the Workflow + the Eventarc trigger.
resource "google_service_account" "runtime" {
  account_id   = "uw-pipeline-sa"
  display_name = "UW pipeline runtime"
}

locals {
  runtime_roles = [
    "roles/aiplatform.user",
    "roles/datastore.user",
    "roles/storage.objectAdmin",
    "roles/run.invoker",
    "roles/workflows.invoker",
    "roles/eventarc.eventReceiver",
    "roles/logging.logWriter",
  ]
}

resource "google_project_iam_member" "runtime" {
  for_each = toset(local.runtime_roles)
  project  = var.project_id
  role     = each.value
  member   = "serviceAccount:${google_service_account.runtime.email}"
}

# Eventarc for GCS needs the Cloud Storage service agent to publish Pub/Sub events.
data "google_storage_project_service_account" "gcs" {}

resource "google_project_iam_member" "gcs_pubsub_publisher" {
  project = var.project_id
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:${data.google_storage_project_service_account.gcs.email_address}"
}
