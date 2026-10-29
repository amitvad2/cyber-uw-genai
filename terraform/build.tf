# Optional in-Terraform image build (local runs: terraform "does everything").
# CI sets build_image=false and builds the image in a dedicated pipeline step instead.
resource "null_resource" "build" {
  count = var.build_image ? 1 : 0

  triggers = {
    tag = var.image_tag
    src = sha1(join("", [for f in sort(fileset("${path.module}/../service", "**")) :
      filesha1("${path.module}/../service/${f}")]))
  }

  provisioner "local-exec" {
    command = "gcloud builds submit ${path.module}/../service --tag ${local.image} --project ${var.project_id}"
  }

  depends_on = [google_project_service.apis]
}
