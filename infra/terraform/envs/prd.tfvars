env                     = "prd"
project_id              = "functional-agent-prd"
region                  = "us-central1"
cloud_run_min_instances = 0 # decisão do PO (2026-11-14): sem instância mínima; cold start aceito
cloud_run_max_instances = 20
enable_pitr_and_backups = true
deletion_protection     = true
monthly_budget_usd      = 200
# billing_account_id: passe por TF_VAR_billing_account_id (variable do GitHub Environment).
