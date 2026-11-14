variable "project_id" { type = string }
variable "billing_account_id" { type = string }
variable "monthly_budget_usd" { type = number }

data "google_project" "this" {
  project_id = var.project_id
}

# Alertas em 50/90/100% do orçamento mensal (F02-RT-07), enviados aos administradores de
# faturamento da conta.
resource "google_billing_budget" "monthly" {
  billing_account = var.billing_account_id
  display_name    = "${var.project_id} mensal"

  budget_filter {
    projects = ["projects/${data.google_project.this.number}"]
  }

  amount {
    specified_amount {
      currency_code = "USD"
      units         = tostring(var.monthly_budget_usd)
    }
  }

  threshold_rules {
    threshold_percent = 0.5
  }
  threshold_rules {
    threshold_percent = 0.9
  }
  threshold_rules {
    threshold_percent = 1.0
  }
}
