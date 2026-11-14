variable "project_id" { type = string }
variable "prefix" { type = string }
variable "github_repository" { type = string }
variable "deployer_environments" { type = list(string) }
variable "terraform_environment" { type = string }
variable "runtime_sa_name" { type = string }
variable "artifact_registry_id" { type = string }
variable "artifact_registry_loc" { type = string }

# Workload Identity Federation: o GitHub Actions troca o token OIDC do job por credenciais
# temporárias. Nenhuma chave JSON de service account existe (F02-RT-02).
# Só jobs deste repositório que rodam nos GitHub Environments do app obtêm token:
# "prd"/"preview" para deploy (deploy.yml, preview.yml) e "infra-prd" para Terraform (infra.yml).
locals {
  allowed_environments = concat(var.deployer_environments, [var.terraform_environment])
  attribute_condition = format(
    "assertion.repository == \"%s\" && assertion.environment in [%s]",
    var.github_repository,
    join(", ", [for e in local.allowed_environments : "\"${e}\""]),
  )
}

resource "google_iam_workload_identity_pool" "github" {
  project                   = var.project_id
  workload_identity_pool_id = "${var.prefix}-github"
  display_name              = "SpecFlow AI: GitHub Actions"
}

resource "google_iam_workload_identity_pool_provider" "github" {
  project                            = var.project_id
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = "github"
  display_name                       = "GitHub OIDC"

  attribute_mapping = {
    "google.subject"         = "assertion.sub"
    "attribute.repository"   = "assertion.repository"
    "attribute.ref"          = "assertion.ref"
    "attribute.environment"  = "assertion.environment"
    "attribute.event_name"   = "assertion.event_name"
    "attribute.workflow_ref" = "assertion.job_workflow_ref"
  }
  attribute_condition = local.attribute_condition

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

locals {
  pool = google_iam_workload_identity_pool.github.name
  # O provider já restringe o repositório; aqui cada SA aceita só os seus GitHub Environments.
  env_principal = "principalSet://iam.googleapis.com/${local.pool}/attribute.environment"
}

# ---- deployer: publica imagem, revisões do Cloud Run e o Hosting (deploy.yml / preview.yml)
resource "google_service_account" "deployer" {
  project      = var.project_id
  account_id   = "${var.prefix}-deployer"
  display_name = "SpecFlow AI: GitHub Actions deploy"
}

# Papéis de projeto: run.developer e firebasehosting.admin não têm escopo por serviço/site que
# cubra o fluxo de deploy; o alcance real fica limitado pelo WIF (só este repositório/environment).
resource "google_project_iam_member" "deployer" {
  for_each = toset([
    "roles/run.developer",
    "roles/firebasehosting.admin",
    "roles/monitoring.viewer", # leitura das métricas do canário
  ])
  project = var.project_id
  role    = each.value
  member  = google_service_account.deployer.member
}

resource "google_artifact_registry_repository_iam_member" "deployer_writer" {
  project    = var.project_id
  location   = var.artifact_registry_loc
  repository = var.artifact_registry_id
  role       = "roles/artifactregistry.writer"
  member     = google_service_account.deployer.member
}

resource "google_service_account_iam_member" "deployer_acts_as_runtime" {
  service_account_id = var.runtime_sa_name
  role               = "roles/iam.serviceAccountUser"
  member             = google_service_account.deployer.member
}

resource "google_service_account_iam_member" "deployer_wif" {
  for_each           = toset(var.deployer_environments)
  service_account_id = google_service_account.deployer.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "${local.env_principal}/${each.value}"
}

# ---- terraform: usado só por infra.yml (apply com aprovação no GitHub Environment).
# Criado no primeiro apply local do bootstrap; depois o próprio Terraform o mantém.
resource "google_service_account" "terraform" {
  project      = var.project_id
  account_id   = "${var.prefix}-terraform"
  display_name = "SpecFlow AI: GitHub Actions terraform"
}

# Owner do projeto compartilhado: necessário para IAM, APIs e WIF. O alcance fica limitado pelo
# WIF (environment infra-prd, com revisores) e pelo código revisado em PR.
resource "google_project_iam_member" "terraform_owner" {
  project = var.project_id
  role    = "roles/owner"
  member  = google_service_account.terraform.member
}

resource "google_service_account_iam_member" "terraform_wif" {
  service_account_id = google_service_account.terraform.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "${local.env_principal}/${var.terraform_environment}"
}

output "provider_name" { value = google_iam_workload_identity_pool_provider.github.name }
output "deployer_email" { value = google_service_account.deployer.email }
output "terraform_email" { value = google_service_account.terraform.email }
