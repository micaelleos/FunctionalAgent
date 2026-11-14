variable "project_id" { type = string }
variable "hosting_site_id" { type = string }

# O projeto já é um projeto Firebase compartilhado (portfólio): não é gerenciado aqui, nem a
# configuração de Auth/Identity Platform, que vale para todos os apps (F02-RT-09).

resource "google_firebase_web_app" "app" {
  provider        = google-beta
  project         = var.project_id
  display_name    = "SpecFlow AI"
  deletion_policy = "DELETE"
}

data "google_firebase_web_app_config" "app" {
  provider   = google-beta
  project    = var.project_id
  web_app_id = google_firebase_web_app.app.app_id
}

# Site criado pelo PO no console; importado no módulo raiz (bloco import em main.tf).
resource "google_firebase_hosting_site" "app" {
  provider = google-beta
  project  = var.project_id
  site_id  = var.hosting_site_id
  app_id   = google_firebase_web_app.app.app_id

  lifecycle {
    prevent_destroy = true
  }
}

output "hosting_site_id" { value = google_firebase_hosting_site.app.site_id }

# Configuração pública do Firebase (não é segredo): vira VITE_FIREBASE_* no build do SPA.
output "web_app_config" {
  value = {
    apiKey            = data.google_firebase_web_app_config.app.api_key
    authDomain        = data.google_firebase_web_app_config.app.auth_domain
    projectId         = var.project_id
    appId             = google_firebase_web_app.app.app_id
    messagingSenderId = data.google_firebase_web_app_config.app.messaging_sender_id
    measurementId     = data.google_firebase_web_app_config.app.measurement_id
  }
}
