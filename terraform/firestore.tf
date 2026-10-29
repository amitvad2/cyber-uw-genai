# Named database, isolated from any existing (default) database on the project.
resource "google_firestore_database" "uw" {
  name        = var.firestore_db
  location_id = var.region
  type        = "FIRESTORE_NATIVE"
  depends_on  = [google_project_service.apis]
}
