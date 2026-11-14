# Infraestrutura do SpecFlow AI (F02). Aplicada localmente com `terraform apply`; o deploy das
# aplicações (imagem do Cloud Run, conteúdo do Hosting) é feito por `make deploy` (ADR-006).

locals {
  p = var.app_prefix
  # Origens do SPA aceitas pelo CORS da API (ADR-002).
  cors_origins = ["https://${var.hosting_site_id}.web.app", "https://${var.hosting_site_id}.firebaseapp.com"]
}

module "project_services" {
  source     = "./modules/project_services"
  project_id = var.project_id
}

module "artifact_registry" {
  source        = "./modules/artifact_registry"
  project_id    = var.project_id
  region        = var.region
  repository_id = local.p
  depends_on    = [module.project_services]
}

module "firestore" {
  source              = "./modules/firestore"
  project_id          = var.project_id
  region              = var.region
  database_id         = local.p
  rules_file          = "${path.root}/../../firestore.rules"
  deletion_protection = var.deletion_protection
  depends_on          = [module.project_services]
}

resource "google_service_account" "api_runtime" {
  project      = var.project_id
  account_id   = "${local.p}-api"
  display_name = "SpecFlow AI: Cloud Run (runtime)"
  depends_on   = [module.project_services]
}

# Papéis do runtime (05-infraestrutura.md §3). O acesso ao Firestore é condicionado ao banco do
# app, para não alcançar os bancos dos outros apps do portfólio. Secret e chave KMS têm IAM no
# próprio recurso. Nada além disto (F02-RT-03).
resource "google_project_iam_member" "api_runtime_firestore" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = google_service_account.api_runtime.member
  condition {
    title      = "${local.p}-database-only"
    expression = "resource.name == \"${module.firestore.database_name}\""
  }
}

resource "google_project_iam_member" "api_runtime" {
  for_each = toset([
    "roles/firebaseauth.viewer", # Auth é do projeto (compartilhado entre os apps)
    "roles/cloudtrace.agent",
    "roles/logging.logWriter",
  ])
  project = var.project_id
  role    = each.value
  member  = google_service_account.api_runtime.member
}

module "secrets" {
  source         = "./modules/secrets"
  project_id     = var.project_id
  secret_id      = "${local.p}-llm-api-key"
  accessor_email = google_service_account.api_runtime.email
  depends_on     = [module.project_services]
}

module "kms" {
  source                 = "./modules/kms"
  project_id             = var.project_id
  region                 = var.region
  key_ring_name          = local.p
  encrypter_decrypter_sa = google_service_account.api_runtime.email
  depends_on             = [module.project_services]
}

module "cloud_run" {
  source                = "./modules/cloud_run"
  project_id            = var.project_id
  region                = var.region
  service_name          = "${local.p}-api"
  service_account_email = google_service_account.api_runtime.email
  min_instances         = var.cloud_run_min_instances
  max_instances         = var.cloud_run_max_instances
  firestore_database    = local.p
  cors_origins          = local.cors_origins
  kms_key_name          = module.kms.jira_tokens_key_id
  deletion_protection   = var.deletion_protection
  depends_on            = [module.project_services, google_project_iam_member.api_runtime]
}

module "firebase" {
  source          = "./modules/firebase"
  project_id      = var.project_id
  hosting_site_id = var.hosting_site_id
  depends_on      = [module.project_services]
}

# Web app e site de Hosting já existiam (criados no console); passam a ser gerenciados aqui.
import {
  to = module.firebase.google_firebase_web_app.app
  id = "projects/${var.project_id}/webApps/${var.firebase_web_app_id}"
}

import {
  to = module.firebase.google_firebase_hosting_site.app
  id = "projects/${var.project_id}/sites/${var.hosting_site_id}"
}
