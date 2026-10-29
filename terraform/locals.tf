locals {
  image = "${var.region}-docker.pkg.dev/${var.project_id}/uw-pipeline/uw-service:${var.image_tag}"

  services = {
    "uw-extract"  = "extract"
    "uw-index"    = "index"
    "uw-evaluate" = "evaluate"
  }

  apis = [
    "run.googleapis.com",
    "workflows.googleapis.com",
    "eventarc.googleapis.com",
    "firestore.googleapis.com",
    "artifactregistry.googleapis.com",
    "cloudbuild.googleapis.com",
    "pubsub.googleapis.com",
    "aiplatform.googleapis.com",
    "logging.googleapis.com",
  ]
}
