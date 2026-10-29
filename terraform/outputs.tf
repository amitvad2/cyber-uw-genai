output "intake_bucket" {
  value = google_storage_bucket.intake.name
}

output "extract_url" {
  value = google_cloud_run_v2_service.svc["uw-extract"].uri
}

output "index_url" {
  value = google_cloud_run_v2_service.svc["uw-index"].uri
}

output "evaluate_url" {
  value = google_cloud_run_v2_service.svc["uw-evaluate"].uri
}

output "workflow" {
  value = google_workflows_workflow.pipeline.name
}

output "eventarc_trigger" {
  value = google_eventarc_trigger.intake.name
}
