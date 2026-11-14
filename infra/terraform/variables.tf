variable "env" {
  description = "Ambiente: dev ou prd."
  type        = string
  validation {
    condition     = contains(["dev", "prd"], var.env)
    error_message = "env deve ser dev ou prd."
  }
}

variable "project_id" {
  description = "Projeto GCP/Firebase do ambiente (ex.: functional-agent-dev)."
  type        = string
}

variable "region" {
  description = "Região de Cloud Run, Artifact Registry, Firestore e KMS."
  type        = string
  default     = "us-central1"
}

variable "github_repository" {
  description = "Repositório autorizado a autenticar via WIF (owner/nome)."
  type        = string
  default     = "micaelleos/FunctionalAgent"
}

variable "cloud_run_min_instances" {
  type    = number
  default = 0
}

variable "cloud_run_max_instances" {
  type    = number
  default = 3
}

variable "billing_account_id" {
  description = "Conta de faturamento (XXXXXX-XXXXXX-XXXXXX) usada pelo budget alert."
  type        = string
}

variable "monthly_budget_usd" {
  description = "Orçamento mensal do projeto; alertas em 50/90/100% (F02-RT-07)."
  type        = number
}

variable "enable_pitr_and_backups" {
  description = "PITR (7 dias) + backup diário (14 dias) do Firestore (F02-RT-04: obrigatório em prd)."
  type        = bool
  default     = false
}

variable "deletion_protection" {
  description = "Protege Firestore e Cloud Run contra destroy acidental."
  type        = bool
  default     = true
}
