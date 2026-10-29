# Object lands in the intake bucket -> run the Workflow. The "drop a file, it runs" trigger.
resource "google_eventarc_trigger" "intake" {
  name            = "uw-intake-trigger"
  location        = var.region
  service_account = google_service_account.runtime.email

  matching_criteria {
    attribute = "type"
    value     = "google.cloud.storage.object.v1.finalized"
  }
  matching_criteria {
    attribute = "bucket"
    value     = google_storage_bucket.intake.name
  }

  destination {
    workflow = google_workflows_workflow.pipeline.id
  }

  depends_on = [
    google_project_iam_member.gcs_pubsub_publisher,
    google_project_iam_member.runtime,
  ]
}
