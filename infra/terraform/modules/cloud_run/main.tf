variable "project_id" { type = string }
variable "region" { type = string }
variable "env" { type = string }
variable "service_account_email" { type = string }
variable "min_instances" { type = number }
variable "max_instances" { type = number }
variable "cors_origins" { type = list(string) }
variable "cors_origin_regex" { type = string }
variable "kms_key_name" { type = string }
variable "deletion_protection" { type = bool }

# O Terraform cria o serviço e a configuração (F02-RT-05); a imagem e o tráfego pertencem ao
# pipeline (deploy.yml), que publica sempre por digest. Por isso image/traffic são ignorados.
resource "google_cloud_run_v2_service" "api" {
  project             = var.project_id
  name                = "api"
  location            = var.region
  ingress             = "INGRESS_TRAFFIC_ALL" # público; autenticação na aplicação (ADR-002)
  deletion_protection = var.deletion_protection

  template {
    service_account                  = var.service_account_email
    timeout                          = "300s"
    max_instance_request_concurrency = 40

    scaling {
      min_instance_count = var.min_instances
      max_instance_count = var.max_instances
    }

    containers {
      # Imagem inicial pública; substituída no primeiro deploy pelo pipeline.
      image = "us-docker.pkg.dev/cloudrun/container/hello"

      ports {
        container_port = 8080
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "1Gi"
        }
        cpu_idle          = true
        startup_cpu_boost = true
      }

      env {
        name  = "ENV"
        value = var.env
      }
      env {
        name  = "GCP_PROJECT"
        value = var.project_id
      }
      env {
        name  = "CORS_ORIGINS"
        value = jsonencode(var.cors_origins)
      }
      env {
        name  = "CORS_ORIGIN_REGEX"
        value = var.cors_origin_regex
      }
      env {
        name  = "KMS_KEY_NAME"
        value = var.kms_key_name
      }
      # LLM_API_KEY (secret llm-api-key) entra na F05, quando o backend passar a usá-lo:
      # montar um secret sem versão impede a revisão de subir.

      startup_probe {
        http_get {
          path = "/healthz"
          port = 8080
        }
        initial_delay_seconds = 0
        period_seconds        = 3
        timeout_seconds       = 2
        failure_threshold     = 10
      }
      liveness_probe {
        http_get {
          path = "/healthz"
          port = 8080
        }
        period_seconds    = 30
        timeout_seconds   = 3
        failure_threshold = 3
      }
    }
  }

  lifecycle {
    ignore_changes = [
      template[0].containers[0].image,
      template[0].revision,
      template[0].labels,
      template[0].annotations,
      client,
      client_version,
      traffic,
    ]
  }
}

# A API é pública na borda; toda rota além de /healthz exige ID token do Firebase (F03).
resource "google_cloud_run_v2_service_iam_member" "public" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.api.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

output "service_name" { value = google_cloud_run_v2_service.api.name }
output "url" { value = google_cloud_run_v2_service.api.uri }
