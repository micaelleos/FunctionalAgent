# SpecFlow AI vive no projeto compartilhado do portfólio (decisão do PO, 2026-11-14): um único
# ambiente (produção) + previews por PR. Todo recurso deste módulo tem o prefixo `app_prefix`
# (ou é o site de Hosting do app) e nada compartilhado do projeto é alterado (F02-RT-09).

variable "project_id" {
  description = "Projeto GCP/Firebase compartilhado do portfólio."
  type        = string
}

variable "region" {
  description = "Região de Cloud Run, Artifact Registry, Firestore e KMS."
  type        = string
  default     = "us-central1"
}

variable "app_prefix" {
  description = "Prefixo dos recursos do app dentro do projeto compartilhado."
  type        = string
  default     = "specflow"
}

variable "hosting_site_id" {
  description = "Site do Firebase Hosting do app (já existente; importado pelo Terraform)."
  type        = string
}

variable "firebase_web_app_id" {
  description = "Web app do Firebase do app (já existente, criado no console; importado)."
  type        = string
}

variable "cloud_run_min_instances" {
  type    = number
  default = 0
}

variable "cloud_run_max_instances" {
  type    = number
  default = 10
}

variable "llm_model" {
  description = "Modelo Gemini do agente no Vertex AI (F05-RT-09, ADR-008)."
  type        = string
  default     = "gemini-3.5-flash-lite"
}

variable "llm_location" {
  description = "Região do Vertex AI para o Gemini (global atende os modelos Gemini 3.x)."
  type        = string
  default     = "global"
}

variable "deletion_protection" {
  description = "Protege o banco Firestore e o Cloud Run contra destroy acidental."
  type        = bool
  default     = true
}

# ---- F11: observabilidade, limites e App Check -------------------------------------------------

variable "alert_email" {
  description = "E-mail que recebe os alertas. O repo é público: passe por TF_VAR_alert_email no apply, nunca no tfvars."
  type        = string
  sensitive   = true
}

variable "uptime_path" {
  description = "Rota do uptime check; só muda no ensaio do AT-F11-03 (docs/runbooks/alertas.md)."
  type        = string
  default     = "/health"
}

variable "daily_cost_alert_usd" {
  description = "Custo estimado de LLM por dia (USD) que dispara o alerta de custo."
  type        = number
  default     = 2
}

variable "app_check_mode" {
  description = "off, monitor (só registra) ou enforce (401 sem token válido). F11-RT-07."
  type        = string
  default     = "monitor"
  validation {
    condition     = contains(["off", "monitor", "enforce"], var.app_check_mode)
    error_message = "app_check_mode deve ser off, monitor ou enforce."
  }
}

variable "daily_message_quota" {
  description = "Mensagens por usuário por dia de Brasília (F11-RT-05)."
  type        = number
  default     = 20
}

variable "daily_token_quota" {
  description = "Tokens (entrada + saída) por usuário por dia de Brasília (F11-RT-05)."
  type        = number
  default     = 200000
}
