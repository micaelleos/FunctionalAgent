# Observabilidade do SpecFlow AI (F11-RT-03/04): métricas por log, dashboard, uptime check, alertas
# por e-mail e SLO. Tudo com o prefixo do app; nada compartilhado do projeto é alterado (F02-RT-09),
# inclusive o budget do projeto: o alerta de custo usa o custo estimado que a API registra.

variable "project_id" { type = string }
variable "prefix" { type = string }
variable "service_name" { type = string }
variable "api_url" { type = string }

variable "alert_email" {
  description = "Quem recebe os alertas. Repo público: passe por TF_VAR_alert_email, nunca no tfvars."
  type        = string
  sensitive   = true
}

variable "uptime_path" {
  description = "Rota do uptime check (o ensaio do AT-F11-03 aponta para uma rota que falha)."
  type        = string
  default     = "/health"
}

variable "daily_cost_alert_usd" {
  description = "Custo estimado de LLM por dia (USD) que dispara o alerta."
  type        = number
  default     = 2
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

# ---- Uptime, canal e alertas -----------------------------------------------------------------

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

resource "google_monitoring_notification_channel" "email" {
  project      = var.project_id
  display_name = "${var.prefix}-alerts"
  type         = "email"
  labels       = { email_address = var.alert_email }
}

locals {
  channels = [google_monitoring_notification_channel.email.id]
  docs     = "Runbooks: https://github.com/micaelleos/FunctionalAgent/tree/master/docs/runbooks"
}

resource "google_monitoring_alert_policy" "errors_5xx" {
  project               = var.project_id
  display_name          = "${var.prefix}: API 5xx > 2%"
  combiner              = "OR"
  notification_channels = local.channels
  documentation { content = "Mais de 2% das respostas da API com 5xx em 5 min. ${local.docs}" }
  conditions {
    display_name = "5xx / total > 2%"
    condition_threshold {
      filter             = "metric.type=\"run.googleapis.com/request_count\" AND ${local.rev} AND metric.label.response_code_class=\"5xx\""
      denominator_filter = "metric.type=\"run.googleapis.com/request_count\" AND ${local.rev}"
      comparison         = "COMPARISON_GT"
      threshold_value    = 0.02
      duration           = "0s"
      aggregations {
        alignment_period     = "300s"
        per_series_aligner   = "ALIGN_DELTA"
        cross_series_reducer = "REDUCE_SUM"
      }
      denominator_aggregations {
        alignment_period     = "300s"
        per_series_aligner   = "ALIGN_DELTA"
        cross_series_reducer = "REDUCE_SUM"
      }
    }
  }
}

resource "google_monitoring_alert_policy" "turn_latency" {
  project               = var.project_id
  display_name          = "${var.prefix}: p95 do turno > 30 s"
  combiner              = "OR"
  notification_channels = local.channels
  documentation { content = "O p95 da duração do turno do agente passou de 30 s em 10 min. ${local.docs}" }
  conditions {
    display_name = "p95 turn_latency_ms > 30000"
    condition_threshold {
      filter          = "metric.type=\"${local.metric}/turn_latency_ms\" AND resource.type=\"cloud_run_revision\""
      comparison      = "COMPARISON_GT"
      threshold_value = 30000
      duration        = "0s"
      aggregations {
        alignment_period     = "600s"
        per_series_aligner   = "ALIGN_DELTA"
        cross_series_reducer = "REDUCE_PERCENTILE_95"
      }
    }
  }
  depends_on = [google_logging_metric.distribution]
}

resource "google_monitoring_alert_policy" "llm_errors" {
  project               = var.project_id
  display_name          = "${var.prefix}: erro do modelo > 5%"
  combiner              = "OR"
  notification_channels = local.channels
  documentation { content = "Mais de 5% dos turnos falharam no modelo (indisponível ou tempo esgotado) em 15 min. ${local.docs}" }
  conditions {
    display_name = "turnos com erro do modelo / turnos > 5%"
    condition_threshold {
      filter             = "metric.type=\"${local.metric}/chat_turns\" AND resource.type=\"cloud_run_revision\" AND metric.label.error=one_of(\"llm-unavailable\",\"turn-timeout\")"
      denominator_filter = "metric.type=\"${local.metric}/chat_turns\" AND resource.type=\"cloud_run_revision\""
      comparison         = "COMPARISON_GT"
      threshold_value    = 0.05
      duration           = "0s"
      aggregations {
        alignment_period     = "900s"
        per_series_aligner   = "ALIGN_DELTA"
        cross_series_reducer = "REDUCE_SUM"
      }
      denominator_aggregations {
        alignment_period     = "900s"
        per_series_aligner   = "ALIGN_DELTA"
        cross_series_reducer = "REDUCE_SUM"
      }
    }
  }
  depends_on = [google_logging_metric.chat_turns]
}

resource "google_monitoring_alert_policy" "jira_failures" {
  project               = var.project_id
  display_name          = "${var.prefix}: falhas ao escrever no Jira"
  combiner              = "OR"
  notification_channels = local.channels
  documentation { content = "3 ou mais ações confirmadas falharam no Jira em 15 min. ${local.docs}" }
  conditions {
    display_name = "jira_writes result=failed >= 3"
    condition_threshold {
      filter          = "metric.type=\"${local.metric}/jira_writes\" AND resource.type=\"cloud_run_revision\" AND metric.label.result=\"failed\""
      comparison      = "COMPARISON_GT"
      threshold_value = 2
      duration        = "0s"
      aggregations {
        alignment_period     = "900s"
        per_series_aligner   = "ALIGN_DELTA"
        cross_series_reducer = "REDUCE_SUM"
      }
    }
  }
  depends_on = [google_logging_metric.counter]
}

resource "google_monitoring_alert_policy" "uptime" {
  project               = var.project_id
  display_name          = "${var.prefix}: API fora do ar (uptime /health)"
  combiner              = "OR"
  notification_channels = local.channels
  documentation { content = "O uptime check de ${var.uptime_path} falhou em mais de uma região por 10 min. ${local.docs}" }
  conditions {
    display_name = "uptime check falhando"
    condition_threshold {
      filter          = "metric.type=\"monitoring.googleapis.com/uptime_check/check_passed\" AND resource.type=\"uptime_url\" AND metric.label.check_id=\"${google_monitoring_uptime_check_config.api.uptime_check_id}\""
      comparison      = "COMPARISON_GT"
      threshold_value = 1
      duration        = "600s"
      aggregations {
        alignment_period     = "1200s"
        per_series_aligner   = "ALIGN_NEXT_OLDER"
        cross_series_reducer = "REDUCE_COUNT_FALSE"
        group_by_fields      = ["resource.label.host"]
      }
    }
  }
}

resource "google_monitoring_alert_policy" "daily_cost" {
  project               = var.project_id
  display_name          = "${var.prefix}: custo estimado de LLM > US$ ${var.daily_cost_alert_usd}/dia"
  combiner              = "OR"
  notification_channels = local.channels
  documentation { content = "O custo estimado do Gemini nas últimas 24 h passou de US$ ${var.daily_cost_alert_usd}. Veja o runbook de custo. ${local.docs}" }
  conditions {
    display_name = "soma de cost_usd em 24 h"
    condition_prometheus_query_language {
      query               = "sum(increase(logging_googleapis_com:user_${var.prefix}_cost_usd_sum{monitored_resource=\"cloud_run_revision\"}[1d])) > ${var.daily_cost_alert_usd}"
      duration            = "0s"
      evaluation_interval = "3600s"
    }
  }
  depends_on = [google_logging_metric.distribution]
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
        plotType = "LINE"
        timeSeriesQuery = {
          timeSeriesFilter = {
            filter      = v.filter
            aggregation = { alignmentPeriod = "300s", perSeriesAligner = v.aligner, crossSeriesReducer = v.reducer, groupByFields = v.group }
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
      tiles = [for i, k in local.order : {
        xPos   = (i % 2) * 6
        yPos   = floor(i / 2) * 4
        width  = 6
        height = 4
        widget = local.tile[k]
      }]
    }
  })
  depends_on = [google_logging_metric.chat_turns, google_logging_metric.distribution, google_logging_metric.counter]
}

output "uptime_check_id" { value = google_monitoring_uptime_check_config.api.uptime_check_id }
output "dashboard_id" { value = google_monitoring_dashboard.app.id }
