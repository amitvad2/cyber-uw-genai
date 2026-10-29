resource "google_workflows_workflow" "pipeline" {
  name            = "uw-pipeline"
  region          = var.region
  service_account = google_service_account.runtime.email

  source_contents = templatefile("${path.module}/../workflows/pipeline.yaml.tftpl", {
    extract_url  = google_cloud_run_v2_service.svc["uw-extract"].uri
    index_url    = google_cloud_run_v2_service.svc["uw-index"].uri
    evaluate_url = google_cloud_run_v2_service.svc["uw-evaluate"].uri
  })

  depends_on = [google_project_service.apis]
}
