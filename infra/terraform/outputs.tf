output "api_url" {
  description = "URL do Cloud Run (o make deploy aponta o SPA para ela)."
  value       = module.cloud_run.url
}

output "image_base" {
  description = "Repositório da imagem no Artifact Registry."
  value       = module.artifact_registry.image_base
}

output "firebase_web_config" {
  description = "Configuração do web app do Firebase (pública; vai para o SPA na F03)."
  value       = module.firebase.web_app_config
}

output "app_check_site_key" {
  description = "Site key do reCAPTCHA Enterprise do App Check (pública; vai para o SPA no make deploy)."
  value       = module.firebase.app_check_site_key
}

output "monitoring_dashboard" {
  description = "Dashboard de operação no Cloud Monitoring."
  value       = module.monitoring.dashboard_id
}
