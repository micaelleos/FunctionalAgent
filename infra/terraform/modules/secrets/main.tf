variable "project_id" { type = string }
variable "accessor_email" { type = string }
variable "secret_id" { type = string }

# Só o contêiner do segredo. O valor é inserido fora do Terraform para nunca ir ao estado
# (Constituição III): gcloud secrets versions add <secret_id> --data-file=-
resource "google_secret_manager_secret" "llm_api_key" {
  project   = var.project_id
  secret_id = var.secret_id
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_iam_member" "llm_api_key_accessor" {
  project   = var.project_id
  secret_id = google_secret_manager_secret.llm_api_key.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${var.accessor_email}"
}

output "llm_api_key_secret_id" { value = google_secret_manager_secret.llm_api_key.secret_id }
