variable "project_id" { type = string }
variable "region" { type = string }
variable "database_id" { type = string }
variable "rules_file" { type = string }
variable "deletion_protection" { type = bool }

# Banco próprio do app (não o (default), que é dos outros apps do portfólio).
resource "google_firestore_database" "app" {
  project                           = var.project_id
  name                              = var.database_id
  location_id                       = var.region
  type                              = "FIRESTORE_NATIVE"
  concurrency_mode                  = "OPTIMISTIC"
  point_in_time_recovery_enablement = "POINT_IN_TIME_RECOVERY_ENABLED" # 7 dias (F02-RT-04)
  delete_protection_state           = var.deletion_protection ? "DELETE_PROTECTION_ENABLED" : "DELETE_PROTECTION_DISABLED"
  deletion_policy                   = var.deletion_protection ? "ABANDON" : "DELETE"
}

resource "google_firestore_backup_schedule" "daily" {
  project   = var.project_id
  database  = google_firestore_database.app.name
  retention = "1209600s" # 14 dias
  daily_recurrence {}
}

# Ações propostas expiram sozinhas (F06): TTL no campo expiresAt.
resource "google_firestore_field" "pending_actions_ttl" {
  project    = var.project_id
  database   = google_firestore_database.app.name
  collection = "pending_actions"
  field      = "expiresAt"
  ttl_config {}
  index_config {}
}

# Regras "nega tudo" para clientes, só neste banco (Constituição II.2, F02-RT-04). O backend usa
# o Admin SDK, que ignora as regras.
resource "google_firebaserules_ruleset" "firestore" {
  project = var.project_id
  source {
    files {
      name    = "firestore.rules"
      content = file(var.rules_file)
    }
  }
  depends_on = [google_firestore_database.app]
  lifecycle {
    create_before_destroy = true
  }
}

resource "google_firebaserules_release" "firestore" {
  project      = var.project_id
  name         = "cloud.firestore/${google_firestore_database.app.name}"
  ruleset_name = google_firebaserules_ruleset.firestore.name
  lifecycle {
    replace_triggered_by = [google_firebaserules_ruleset.firestore]
  }
}

output "database_name" {
  description = "Nome completo do banco, usado na condição de IAM do runtime."
  value       = "projects/${var.project_id}/databases/${google_firestore_database.app.name}"
}
