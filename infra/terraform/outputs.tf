# Valores para as variáveis do GitHub Environment do ambiente (infra/bootstrap/README.md §4).
output "github_environment_variables" {
  description = "Cadastre estes valores como variables do GitHub Environment correspondente."
  value = {
    GCP_PROJECT_ID      = var.project_id
    GCP_REGION          = var.region
    GCP_WIF_PROVIDER    = module.wif.provider_name
    GCP_DEPLOYER_SA     = module.wif.deployer_email
    GCP_TERRAFORM_SA    = module.wif.terraform_email
    GCP_ARTIFACT_REPO   = module.artifact_registry.image_base
    CLOUD_RUN_SERVICE   = module.cloud_run.service_name
    FIREBASE_SITE_ID    = module.firebase.hosting_site_id
    API_BASE_URL        = module.cloud_run.url
    FIREBASE_WEB_CONFIG = jsonencode(module.firebase.web_app_config)
  }
}
