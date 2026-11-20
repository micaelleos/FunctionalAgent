variable "project_id" { type = string }
variable "region" { type = string }
variable "service_name" { type = string }
variable "firestore_database" { type = string }
variable "service_account_email" { type = string }
variable "min_instances" { type = number }
variable "max_instances" { type = number }
variable "cors_origins" { type = list(string) }
variable "kms_key_name" { type = string }
variable "deletion_protection" { type = bool }
variable "llm_model" { type = string }
variable "llm_location" { type = string }
variable "project_number" { type = string }
variable "app_check_mode" { type = string }
variable "daily_message_quota" { type = number }
variable "daily_token_quota" { type = number }
variable "monthly_token_budget" { type = number }
variable "confluence_enabled" { type = bool }
variable "confluence_write_enabled" {
  type    = bool
  default = false
}
variable "prompt_version" { type = string }

# O Terraform cria o serviço e a configuração (F02-RT-05); a imagem e o tráfego pertencem ao
# `make deploy` (scripts/deploy.sh), que publica sempre por digest. Por isso image/traffic são ignorados.
resource "google_cloud_run_v2_service" "api" {
  project             = var.project_id
  name                = var.service_name
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
        value = "prd"
      }
      env {
        name  = "FIRESTORE_DATABASE"
        value = var.firestore_database
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
        name  = "KMS_KEY_NAME"
        value = var.kms_key_name
      }
      # Agente (F05, ADR-008): Gemini no Vertex AI pela SA do serviço; não há chave de LLM.
      env {
        name  = "LLM_PROVIDER"
        value = "google_vertexai"
      }
      env {
        name  = "LLM_MODEL"
        value = var.llm_model
      }
      env {
        name  = "LLM_LOCATION"
        value = var.llm_location
      }

      # Observabilidade, limites e App Check (F11).
      env {
        name  = "TRACING_ENABLED"
        value = "true"
      }
      env {
        name  = "FIREBASE_PROJECT_NUMBER"
        value = var.project_number
      }
      env {
        name  = "APP_CHECK_MODE"
        value = var.app_check_mode
      }
      env {
        name  = "DAILY_MESSAGE_QUOTA"
        value = tostring(var.daily_message_quota)
      }
      env {
        name  = "DAILY_TOKEN_QUOTA"
        value = tostring(var.daily_token_quota)
      }
      env {
        name  = "MONTHLY_TOKEN_BUDGET"
        value = tostring(var.monthly_token_budget)
      }
      env {
        name  = "CONFLUENCE_ENABLED"
        value = tostring(var.confluence_enabled)
      }
      env {
        name  = "CONFLUENCE_WRITE_ENABLED"
        value = tostring(var.confluence_write_enabled)
      }
      env {
        name  = "PROMPT_VERSION"
        value = var.prompt_version
      }

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

  # template.revision NÃO é ignorado: fica vazio para o Cloud Run gerar nomes. O `make deploy` usa a
  # API v2 sem nomear revisões; com um nome fixado, mudar a configuração aqui daria 409.
  lifecycle {
    ignore_changes = [
      template[0].containers[0].image,
      template[0].labels,
      template[0].annotations,
      client,
      client_version,
      traffic,
      scaling, # escala no nível do serviço não é usada; a API devolve um bloco vazio (diff perpétuo)
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
