variable "project_id" {
  type    = string
  default = "bt-mvp-dev-eu"
}

variable "region" {
  type    = string
  default = "europe-west2"
}

variable "github_repo" {
  type        = string
  description = "GitHub repo in owner/name form, e.g. amitvadhel/cyber-uw-genai"
}
