# Único ambiente (decisão do PO, 2026-11-14): produção no projeto compartilhado do portfólio.
project_id              = "pcb-inspect"
region                  = "us-central1"
app_prefix              = "specflow"
hosting_site_id         = "specsflow-ai"
cloud_run_min_instances = 0 # cold start aceito
cloud_run_max_instances = 10
deletion_protection     = true
