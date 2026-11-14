variable "project_id" { type = string }
variable "region" { type = string }
variable "rules_file" { type = string }
variable "enable_pitr_and_backups" { type = bool }
variable "deletion_protection" { type = bool }

resource "google_firestore_database" "default" {
  project                           = var.project_id
  name                              = "(default)"
  location_id                       = var.region
  type                              = "FIRESTORE_NATIVE"
  concurrency_mode                  = "OPTIMISTIC"
  point_in_time_recovery_enablement = var.enable_pitr_and_backups ? "POINT_IN_TIME_RECOVERY_ENABLED" : "POINT_IN_TIME_RECOVERY_DISABLED"
  delete_protection_state           = var.deletion_protection ? "DELETE_PROTECTION_ENABLED" : "DELETE_PROTECTION_DISABLED"
  deletion_policy                   = var.deletion_protection ? "ABANDON" : "DELETE"
}

resource "google_firestore_backup_schedule" "daily" {
  count     = var.enable_pitr_and_backups ? 1 : 0
  project   = var.project_id
  database  = google_firestore_database.default.name
  retention = "1209600s" # 14 dias
  daily_recurrence {}
}

# Ações propostas expiram sozinhas (F06): TTL no campo expiresAt.
resource "google_firestore_field" "pending_actions_ttl" {
  project    = var.project_id
  database   = google_firestore_database.default.name
  collection = "pending_actions"
  field      = "expiresAt"
  ttl_config {}
  index_config {}
}

# Regras "nega tudo" para clientes (Constituição II.2, F02-RT-04). O backend usa o Admin SDK,
# que ignora as regras.
resource "google_firebaserules_ruleset" "firestore" {
  project = var.project_id
  source {
    files {
      name    = "firestore.rules"
      content = file(var.rules_file)
    }
  }
  depends_on = [google_firestore_database.default]
  lifecycle {
    create_before_destroy = true
  }
}

resource "google_firebaserules_release" "firestore" {
  project      = var.project_id
  name         = "cloud.firestore"
  ruleset_name = google_firebaserules_ruleset.firestore.name
  lifecycle {
    replace_triggered_by = [google_firebaserules_ruleset.firestore]
  }
}
