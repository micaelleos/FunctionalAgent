variable "project_id" { type = string }
variable "region" { type = string }
variable "repository_id" { type = string }

resource "google_artifact_registry_repository" "api" {
  project       = var.project_id
  location      = var.region
  repository_id = var.repository_id
  format        = "DOCKER"
  description   = "Imagens do backend (deploy sempre por digest)"

  # O Cloud Run baixa a imagem a cada cold start (min-instances=0), então a imagem da revisão no ar
  # precisa existir; a anterior fica para rollback. O resto é apagado (a limpeza roda ~1x por dia).
  cleanup_policy_dry_run = false
  cleanup_policies {
    id     = "manter-3-ultimas"
    action = "KEEP"
    most_recent_versions {
      keep_count = 3
    }
  }
  cleanup_policies {
    id     = "apagar-o-resto"
    action = "DELETE"
    condition {
      older_than = "86400s" # 1 dia; as 3 mais recentes são mantidas pela regra KEEP
    }
  }
}

output "repository_id" { value = google_artifact_registry_repository.api.repository_id }
output "image_base" {
  value = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.api.repository_id}/api"
}
