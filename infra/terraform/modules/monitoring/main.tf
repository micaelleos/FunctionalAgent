# Observabilidade do SpecFlow AI (F11-RT-03/04): métricas por log, dashboard, uptime check e SLO.
# Tudo com o prefixo do app; nada compartilhado do projeto é alterado (F02-RT-09). Os alertas por
# e-mail saíram em 2026-11-20 por custo (decisão do PO); o custo do Gemini é limitado pelo teto
# mensal do beta (F12-RF-05). Para recriá-los, veja docs/runbooks/monitoramento.md.

variable "project_id" { type = string }
variable "prefix" { type = string }
variable "service_name" { type = string }
variable "api_url" { type = string }

variable "uptime_path" {
  description = "Rota do uptime check (o ensaio do AT-F11-03 aponta para uma rota que falha)."
  type        = string
  default     = "/health"
}

locals {
  api_host = trimprefix(var.api_url, "https://")
  run      = "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"${var.service_name}\""
  event    = { for e in ["chat_turn", "jira_write", "action_proposed", "usage_limit", "app_check", "client_error"] : e => "${local.run} AND jsonPayload.event=\"${e}\"" }
  metric   = "logging.googleapis.com/user/${var.prefix}"
  rev      = "resource.type=\"cloud_run_revision\" AND resource.label.service_name=\"${var.service_name}\""
}

# ---- Métricas por log ------------------------------------------------------------------------

resource "google_logging_metric" "chat_turns" {
  project = var.project_id
  name    = "${var.prefix}/chat_turns"
  filter  = local.event.chat_turn
  metric_descriptor {
    metric_kind = "DELTA"
    value_type  = "INT64"
    labels {
      key         = "error"
      description = "Código do erro do turno (vazio quando deu certo)"
    }
  }
  label_extractors = { error = "EXTRACT(jsonPayload.error)" }
}

resource "google_logging_metric" "distribution" {
  for_each = {
    turn_latency_ms        = { field = "duration_ms", unit = "ms", scale = 100, growth = 2 }
    first_token_latency_ms = { field = "first_token_ms", unit = "ms", scale = 100, growth = 2 }
    input_tokens           = { field = "input_tokens", unit = "1", scale = 100, growth = 3 }
    output_tokens          = { field = "output_tokens", unit = "1", scale = 10, growth = 3 }
    cost_usd               = { field = "cost_usd", unit = "USD", scale = 0.0001, growth = 3 }
  }
  project = var.project_id
  name    = "${var.prefix}/${each.key}"
  filter  = "${local.event.chat_turn} AND jsonPayload.${each.value.field}>=0"
  metric_descriptor {
    metric_kind = "DELTA"
    value_type  = "DISTRIBUTION"
    unit        = each.value.unit
  }
  value_extractor = "EXTRACT(jsonPayload.${each.value.field})"
  bucket_options {
    exponential_buckets {
      num_finite_buckets = 20
      growth_factor      = each.value.growth
      scale              = each.value.scale
    }
  }
}

resource "google_logging_metric" "counter" {
  for_each = {
    jira_writes      = { event = "jira_write", labels = { result = "EXTRACT(jsonPayload.result)", code = "EXTRACT(jsonPayload.code)" } }
    actions_proposed = { event = "action_proposed", labels = { kind = "EXTRACT(jsonPayload.kind)" } }
    usage_limits     = { event = "usage_limit", labels = { limit = "EXTRACT(jsonPayload.limit)" } }
    app_check        = { event = "app_check", labels = { result = "EXTRACT(jsonPayload.result)" } }
    client_errors    = { event = "client_error", labels = { kind = "EXTRACT(jsonPayload.kind)" } }
  }
  project = var.project_id
  name    = "${var.prefix}/${each.key}"
  filter  = local.event[each.value.event]
  metric_descriptor {
    metric_kind = "DELTA"
    value_type  = "INT64"
    dynamic "labels" {
      for_each = keys(each.value.labels)
      content {
        key = labels.value
      }
    }
  }
  label_extractors = each.value.labels
}

# ---- Uptime check ------------------------------------------------------------------------------

resource "google_monitoring_uptime_check_config" "api" {
  project      = var.project_id
  display_name = "${var.prefix}-api-health"
  timeout      = "10s"
  period       = "300s"
  http_check {
    path         = var.uptime_path
    port         = 443
    use_ssl      = true
    validate_ssl = true
  }
  monitored_resource {
    type   = "uptime_url"
    labels = { project_id = var.project_id, host = local.api_host }
  }
}

# ---- SLO de disponibilidade ------------------------------------------------------------------

resource "google_monitoring_custom_service" "api" {
  project      = var.project_id
  service_id   = "${var.prefix}-api"
  display_name = "SpecFlow AI API"
}

resource "google_monitoring_slo" "availability" {
  project             = var.project_id
  service             = google_monitoring_custom_service.api.service_id
  slo_id              = "${var.prefix}-availability"
  display_name        = "99,5% das requisições sem 5xx (28 dias)"
  goal                = 0.995
  rolling_period_days = 28
  request_based_sli {
    good_total_ratio {
      bad_service_filter   = "metric.type=\"run.googleapis.com/request_count\" AND ${local.rev} AND metric.label.response_code_class=\"5xx\""
      total_service_filter = "metric.type=\"run.googleapis.com/request_count\" AND ${local.rev}"
    }
  }
}

# ---- Dashboard -------------------------------------------------------------------------------

locals {
  tile = { for k, v in {
    requests  = { title = "Requisições por classe", filter = "metric.type=\"run.googleapis.com/request_count\" AND ${local.rev}", aligner = "ALIGN_RATE", reducer = "REDUCE_SUM", group = ["metric.label.response_code_class"] }
    turns     = { title = "Turnos do agente por erro", filter = "metric.type=\"${local.metric}/chat_turns\" AND resource.type=\"cloud_run_revision\"", aligner = "ALIGN_DELTA", reducer = "REDUCE_SUM", group = ["metric.label.error"] }
    p95       = { title = "Duração do turno (p95, ms)", filter = "metric.type=\"${local.metric}/turn_latency_ms\" AND resource.type=\"cloud_run_revision\"", aligner = "ALIGN_DELTA", reducer = "REDUCE_PERCENTILE_95", group = [] }
    ttft      = { title = "1º token (p95, ms)", filter = "metric.type=\"${local.metric}/first_token_latency_ms\" AND resource.type=\"cloud_run_revision\"", aligner = "ALIGN_DELTA", reducer = "REDUCE_PERCENTILE_95", group = [] }
    tokens    = { title = "Tokens de saída por turno (p50)", filter = "metric.type=\"${local.metric}/output_tokens\" AND resource.type=\"cloud_run_revision\"", aligner = "ALIGN_DELTA", reducer = "REDUCE_PERCENTILE_50", group = [] }
    proposals = { title = "Ações propostas", filter = "metric.type=\"${local.metric}/actions_proposed\" AND resource.type=\"cloud_run_revision\"", aligner = "ALIGN_DELTA", reducer = "REDUCE_SUM", group = ["metric.label.kind"] }
    jira      = { title = "Escritas no Jira por resultado", filter = "metric.type=\"${local.metric}/jira_writes\" AND resource.type=\"cloud_run_revision\"", aligner = "ALIGN_DELTA", reducer = "REDUCE_SUM", group = ["metric.label.result", "metric.label.code"] }
    limits    = { title = "Cota e rate limit atingidos", filter = "metric.type=\"${local.metric}/usage_limits\" AND resource.type=\"cloud_run_revision\"", aligner = "ALIGN_DELTA", reducer = "REDUCE_SUM", group = ["metric.label.limit"] }
    appcheck  = { title = "App Check sem token válido", filter = "metric.type=\"${local.metric}/app_check\" AND resource.type=\"cloud_run_revision\"", aligner = "ALIGN_DELTA", reducer = "REDUCE_SUM", group = ["metric.label.result"] }
    client    = { title = "Erros do front", filter = "metric.type=\"${local.metric}/client_errors\" AND resource.type=\"cloud_run_revision\"", aligner = "ALIGN_DELTA", reducer = "REDUCE_SUM", group = ["metric.label.kind"] }
    } : k => {
    title = v.title
    xyChart = {
      dataSets = [{
        plotType   = "LINE"
        targetAxis = "Y1"
        timeSeriesQuery = {
          timeSeriesFilter = {
            filter = v.filter
            # A API omite listas vazias e zeros; enviar igual evita diff perpétuo no plan.
            aggregation = merge(
              { alignmentPeriod = "300s", perSeriesAligner = v.aligner, crossSeriesReducer = v.reducer },
              length(v.group) > 0 ? { groupByFields = v.group } : {},
            )
          }
        }
      }]
    }
  } }
  order = ["requests", "turns", "p95", "ttft", "tokens", "proposals", "jira", "limits", "appcheck", "client"]
}

resource "google_monitoring_dashboard" "app" {
  project = var.project_id
  dashboard_json = jsonencode({
    displayName = "${var.prefix}: operação"
    mosaicLayout = {
      columns = 12
      tiles = [for i, k in local.order : merge(
        { width = 6, height = 4, widget = local.tile[k] },
        i % 2 > 0 ? { xPos = 6 } : {},
        i >= 2 ? { yPos = floor(i / 2) * 4 } : {},
      )]
    }
  })
  depends_on = [google_logging_metric.chat_turns, google_logging_metric.distribution, google_logging_metric.counter]
}

output "uptime_check_id" { value = google_monitoring_uptime_check_config.api.uptime_check_id }
output "dashboard_id" { value = google_monitoring_dashboard.app.id }
