variable "project_id" { type = string }
variable "region" { type = string }
variable "encrypter_decrypter_sa" { type = string }

resource "google_kms_key_ring" "app" {
  project  = var.project_id
  name     = "app"
  location = var.region
}

# Chave dos tokens Jira por usuário (envelope encryption, ADR-004). Rotação a cada 90 dias.
resource "google_kms_crypto_key" "jira_tokens" {
  name            = "jira-tokens"
  key_ring        = google_kms_key_ring.app.id
  rotation_period = "7776000s"
  purpose         = "ENCRYPT_DECRYPT"

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_kms_crypto_key_iam_member" "runtime" {
  crypto_key_id = google_kms_crypto_key.jira_tokens.id
  role          = "roles/cloudkms.cryptoKeyEncrypterDecrypter"
  member        = "serviceAccount:${var.encrypter_decrypter_sa}"
}

output "jira_tokens_key_id" { value = google_kms_crypto_key.jira_tokens.id }
