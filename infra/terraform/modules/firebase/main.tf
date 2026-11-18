variable "project_id" { type = string }
variable "hosting_site_id" { type = string }
variable "app_prefix" { type = string }

# O projeto já é um projeto Firebase compartilhado (portfólio): não é gerenciado aqui, nem a
# configuração de Auth/Identity Platform, que vale para todos os apps (F02-RT-09).

resource "google_firebase_web_app" "app" {
  provider        = google-beta
  project         = var.project_id
  display_name    = "SpecFlow AI"
  deletion_policy = "ABANDON" # nunca apaga o app do console, nem num destroy

  lifecycle {
    prevent_destroy = true
  }
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

# App Check (F11-RT-07): chave reCAPTCHA Enterprise só deste app e o registro do web app. Não há
# enforcement nos serviços do Firebase (Firestore/Auth são do projeto compartilhado): quem exige o
# token é a própria API, pelo APP_CHECK_MODE.
resource "google_recaptcha_enterprise_key" "web" {
  project      = var.project_id
  display_name = "${var.app_prefix}-web"
  web_settings {
    integration_type  = "SCORE"
    allow_all_domains = false
    allowed_domains   = ["${var.hosting_site_id}.web.app", "${var.hosting_site_id}.firebaseapp.com"]
  }
}

resource "google_firebase_app_check_recaptcha_enterprise_config" "web" {
  provider  = google-beta
  project   = var.project_id
  app_id    = google_firebase_web_app.app.app_id
  site_key  = google_recaptcha_enterprise_key.web.name
  token_ttl = "3600s"
}

output "app_check_site_key" { value = google_recaptcha_enterprise_key.web.name }

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
