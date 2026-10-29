# Three independent Cloud Run services from ONE shared image; ROLE selects behaviour.
resource "google_cloud_run_v2_service" "svc" {
  for_each = local.services

  name     = each.key
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = google_service_account.runtime.email

    containers {
      image = local.image
      ports { container_port = 8080 }

      env { name = "ROLE"                  value = each.value }
      env { name = "FIRESTORE_DB"          value = var.firestore_db }
      env { name = "GOOGLE_CLOUD_PROJECT"  value = var.project_id }
      env { name = "GOOGLE_CLOUD_LOCATION" value = var.region }
      env { name = "GEN_MODEL"             value = var.gen_model }
      env { name = "EMB_MODEL"             value = var.emb_model }
    }
  }

  depends_on = [null_resource.build, google_project_iam_member.runtime]
}

# The Workflow (runtime SA) must be allowed to invoke each service. No public access.
resource "google_cloud_run_v2_service_iam_member" "invoker" {
  for_each = google_cloud_run_v2_service.svc
  name     = each.value.name
  location = var.region
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.runtime.email}"
}
