variable "project_id" { type = string }
variable "hosting_site_id" { type = string }

resource "google_firebase_project" "this" {
  provider = google-beta
  project  = var.project_id
}

resource "google_firebase_web_app" "spa" {
  provider        = google-beta
  project         = var.project_id
  display_name    = "Agente Funcional (web)"
  deletion_policy = "DELETE"
  depends_on      = [google_firebase_project.this]
}

data "google_firebase_web_app_config" "spa" {
  provider   = google-beta
  project    = var.project_id
  web_app_id = google_firebase_web_app.spa.app_id
}

resource "google_firebase_hosting_site" "default" {
  provider = google-beta
  project  = var.project_id
  site_id  = var.hosting_site_id
  app_id   = google_firebase_web_app.spa.app_id
}

# Firebase Authentication (Identity Platform). E-mail/senha já habilitado; o provedor Google
# exige um OAuth client e entra na F03.
resource "google_identity_platform_config" "auth" {
  provider = google-beta
  project  = var.project_id

  sign_in {
    allow_duplicate_emails = false
    email {
      enabled           = true
      password_required = true
    }
  }

  authorized_domains = [
    "localhost",
    "${var.hosting_site_id}.web.app",
    "${var.hosting_site_id}.firebaseapp.com",
  ]

  depends_on = [google_firebase_project.this]
}

output "hosting_site_id" { value = google_firebase_hosting_site.default.site_id }

# Configuração pública do Firebase (não é segredo): vira VITE_FIREBASE_* no build do SPA.
output "web_app_config" {
  value = {
    apiKey            = data.google_firebase_web_app_config.spa.api_key
    authDomain        = data.google_firebase_web_app_config.spa.auth_domain
    projectId         = var.project_id
    appId             = google_firebase_web_app.spa.app_id
    messagingSenderId = data.google_firebase_web_app_config.spa.messaging_sender_id
  }
}
