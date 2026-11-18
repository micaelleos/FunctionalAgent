"""Checagem estática do monitoramento (F11-RF-04): os alertas da spec existem no Terraform.

O disparo de verdade é o AT-F11-03 (ensaio em prd, docs/runbooks/alertas.md); aqui garantimos que
nenhum alerta some do módulo sem a spec mudar e que o e-mail do responsável nunca é versionado.
"""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
TF = ROOT / "infra" / "terraform"
MONITORING = (TF / "modules" / "monitoring" / "main.tf").read_text()

# Alertas exigidos pela spec (F11-RF-04, §4) → recurso no módulo.
ALERTS = {
    "errors_5xx": "0.02",  # 5xx > 2% em 5 min
    "turn_latency": "30000",  # p95 do turno > 30 s
    "llm_errors": "0.05",  # erro do modelo > 5%
    "jira_failures": "jira_writes",
    "uptime": "uptime_check/check_passed",
    "daily_cost": "daily_cost_alert_usd",
}


def _resource(kind: str, name: str) -> str:
    match = re.search(
        rf'resource "{kind}" "{name}" \{{(.*?)\n\}}\n', MONITORING, flags=re.DOTALL
    )
    assert match, f"{kind}.{name} não está em modules/monitoring/main.tf"
    return match.group(1)


@pytest.mark.parametrize(("name", "marker"), sorted(ALERTS.items()))
def test_f11_rf_04_alerta_existe_e_notifica_por_email(name: str, marker: str) -> None:
    body = _resource("google_monitoring_alert_policy", name)
    assert marker in body
    assert "notification_channels = local.channels" in body
    assert "documentation" in body  # aponta para os runbooks


def test_f11_rf_04_uptime_e_slo() -> None:
    uptime = _resource("google_monitoring_uptime_check_config", "api")
    assert re.search(r"path\s*=\s*var\.uptime_path", uptime)
    slo = _resource("google_monitoring_slo", "availability")
    assert re.search(r"goal\s*=\s*0\.995", slo)
    assert re.search(r"rolling_period_days\s*=\s*28", slo)


def test_f11_rf_04_email_do_alerta_nunca_versionado() -> None:
    # O repo é público: o e-mail só entra por TF_VAR_alert_email no apply.
    email = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
    for path in [*TF.rglob("*.tf"), *TF.rglob("*.tfvars")]:
        if ".terraform" in path.parts:
            continue
        found = [
            m
            for m in email.findall(path.read_text())
            if not m.endswith(".gserviceaccount.com")
        ]
        assert not found, f"e-mail versionado em {path.relative_to(ROOT)}"
    assert re.search(r'variable "alert_email" \{[^}]*sensitive\s*=\s*true', MONITORING)
