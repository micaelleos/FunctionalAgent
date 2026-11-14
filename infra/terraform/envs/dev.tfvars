env                     = "dev"
project_id              = "functional-agent-dev"
region                  = "us-central1"
cloud_run_min_instances = 0
cloud_run_max_instances = 3
enable_pitr_and_backups = false
deletion_protection     = false
monthly_budget_usd      = 30
# billing_account_id: passe por TF_VAR_billing_account_id (variable do GitHub Environment).
