# Único ambiente (decisão do PO, 2026-11-14): produção no projeto compartilhado do portfólio.
project_id              = "pcb-inspect"
region                  = "us-central1"
app_prefix              = "specflow"
hosting_site_id         = "specsflow-ai"
firebase_web_app_id     = "1:511022267092:web:072bdfbdcb7cb648921941" # "SpecFlow AI"
cloud_run_min_instances = 0                                           # cold start aceito
cloud_run_max_instances = 10
deletion_protection     = true

# F19 ligada em prd (decisão do PO, 2026-11-20): leitura do Confluence e prompt v2 da metodologia.
confluence_enabled = true
prompt_version     = "v2"
