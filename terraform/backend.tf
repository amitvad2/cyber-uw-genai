terraform {
  backend "gcs" {
    bucket = "bt-mvp-dev-eu-tfstate" # created by ../bootstrap; change if your project id differs
    prefix = "cyber-uw-genai"
  }
}
