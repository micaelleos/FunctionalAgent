# Infraestrutura base de um ambiente (F02). Tudo aqui é aplicado por infra.yml; o deploy das
# aplicações (imagem do Cloud Run, conteúdo do Hosting) é feito por deploy.yml/preview.yml.

locals {
  hosting_site_id = var.project_id
  # Origens do SPA aceitas pelo CORS da API: site principal e canais de preview (ADR-002).
  cors_origins      = ["https://${local.hosting_site_id}.web.app", "https://${local.hosting_site_id}.firebaseapp.com"]
  cors_origin_regex = "^https://${local.hosting_site_id}--[a-z0-9-]+\\.web\\.app$"
}

module "project_services" {
  source     = "./modules/project_services"
  project_id = var.project_id
}

module "artifact_registry" {
  source     = "./modules/artifact_registry"
  project_id = var.project_id
  region     = var.region
  depends_on = [module.project_services]
}

module "firestore" {
  source                  = "./modules/firestore"
  project_id              = var.project_id
  region                  = var.region
  rules_file              = "${path.root}/../../firestore.rules"
  enable_pitr_and_backups = var.enable_pitr_and_backups
  deletion_protection     = var.deletion_protection
  depends_on              = [module.project_services, module.firebase]
}

resource "google_service_account" "api_runtime" {
  project      = var.project_id
  account_id   = "api-runtime"
  display_name = "Cloud Run: api (runtime)"
  depends_on   = [module.project_services]
}

# Papéis de projeto do runtime (05-infraestrutura.md §3). Secret e chave KMS têm IAM no próprio
# recurso, nos módulos secrets e kms. Nada além disto (F02-RT-03).
resource "google_project_iam_member" "api_runtime" {
  for_each = toset([
    "roles/datastore.user",
    "roles/firebaseauth.viewer",
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
  accessor_email = google_service_account.api_runtime.email
  depends_on     = [module.project_services]
}

module "kms" {
  source                 = "./modules/kms"
  project_id             = var.project_id
  region                 = var.region
  encrypter_decrypter_sa = google_service_account.api_runtime.email
  depends_on             = [module.project_services]
}

module "cloud_run" {
  source                = "./modules/cloud_run"
  project_id            = var.project_id
  region                = var.region
  env                   = var.env
  service_account_email = google_service_account.api_runtime.email
  min_instances         = var.cloud_run_min_instances
  max_instances         = var.cloud_run_max_instances
  cors_origins          = local.cors_origins
  cors_origin_regex     = local.cors_origin_regex
  kms_key_name          = module.kms.jira_tokens_key_id
  deletion_protection   = var.deletion_protection
  depends_on            = [module.project_services, google_project_iam_member.api_runtime]
}

module "firebase" {
  source          = "./modules/firebase"
  project_id      = var.project_id
  hosting_site_id = local.hosting_site_id
  depends_on      = [module.project_services]
}

module "wif" {
  source                = "./modules/wif"
  project_id            = var.project_id
  github_repository     = var.github_repository
  deployer_environment  = var.env
  terraform_environment = "infra-${var.env}"
  runtime_sa_name       = google_service_account.api_runtime.name
  artifact_registry_id  = module.artifact_registry.repository_id
  artifact_registry_loc = var.region
  depends_on            = [module.project_services]
}

module "budget" {
  source             = "./modules/budget"
  project_id         = var.project_id
  billing_account_id = var.billing_account_id
  monthly_budget_usd = var.monthly_budget_usd
  depends_on         = [module.project_services]
}
