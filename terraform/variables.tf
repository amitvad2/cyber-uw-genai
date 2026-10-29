variable "project_id" {
  type    = string
  default = "bt-mvp-dev-eu"
}

variable "region" {
  type    = string
  default = "europe-west2"
}

variable "firestore_db" {
  type    = string
  default = "uw-demo"
}

variable "gen_model" {
  type    = string
  default = "gemini-3.5-flash"
}

variable "emb_model" {
  type    = string
  default = "text-embedding-005"
}

variable "image_tag" {
  type        = string
  default     = "latest"
  description = "Container image tag. CI passes the git SHA."
}

variable "build_image" {
  type        = bool
  default     = true
  description = "true = Terraform builds+pushes the image via Cloud Build (local runs). CI sets false."
}

variable "github_repo" {
  type        = string
  default     = ""
  description = "Unused here; present so CI can pass it uniformly."
}
