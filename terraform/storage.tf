resource "google_storage_bucket" "intake" {
  name                        = "${var.project_id}-uw-intake"
  location                    = var.region
  uniform_bucket_level_access = true
  force_destroy               = true
  depends_on                  = [google_project_service.apis]
}
