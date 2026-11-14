variable "project_id" { type = string }
variable "region" { type = string }
variable "repository_id" { type = string }

resource "google_artifact_registry_repository" "api" {
  project       = var.project_id
  location      = var.region
  repository_id = var.repository_id
  format        = "DOCKER"
  description   = "Imagens do backend (deploy sempre por digest)"

  cleanup_policy_dry_run = false
  cleanup_policies {
    id     = "manter-20-ultimas"
    action = "KEEP"
    most_recent_versions {
      keep_count = 20
    }
  }
  cleanup_policies {
    id     = "apagar-antigas"
    action = "DELETE"
    condition {
      older_than = "2592000s" # 30 dias; as 20 mais recentes são mantidas pela regra KEEP
    }
  }
}

output "repository_id" { value = google_artifact_registry_repository.api.repository_id }
output "image_base" {
  value = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.api.repository_id}/api"
}
