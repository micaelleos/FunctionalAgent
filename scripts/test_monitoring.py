"""Checagem estática do monitoramento (F11-RF-04): dashboard, uptime check e SLO no Terraform.

Os alertas por e-mail saíram em 2026-11-20 por custo (decisão do PO, docs/runbooks/monitoramento.md);
aqui garantimos que eles não voltam sem a spec mudar, que o que ficou continua lá e que nenhum
e-mail pessoal é versionado (o repo é público).
"""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
TF = ROOT / "infra" / "terraform"
MONITORING = (TF / "modules" / "monitoring" / "main.tf").read_text()


def _resource(kind: str, name: str) -> str:
    match = re.search(
        rf'resource "{kind}" "{name}" \{{(.*?)\n\}}\n', MONITORING, flags=re.DOTALL
    )
    assert match, f"{kind}.{name} não está em modules/monitoring/main.tf"
    return match.group(1)


def test_f11_rf_04_uptime_slo_e_dashboard() -> None:
    uptime = _resource("google_monitoring_uptime_check_config", "api")
    assert re.search(r"path\s*=\s*var\.uptime_path", uptime)
    slo = _resource("google_monitoring_slo", "availability")
    assert re.search(r"goal\s*=\s*0\.995", slo)
    assert re.search(r"rolling_period_days\s*=\s*28", slo)
    _resource("google_monitoring_dashboard", "app")


def test_f11_rf_04_sem_alertas_nem_canal_de_email() -> None:
    for path in TF.rglob("*.tf"):
        if ".terraform" in path.parts:
            continue
        text = path.read_text()
        assert "google_monitoring_alert_policy" not in text, path.relative_to(ROOT)
        assert "google_monitoring_notification_channel" not in text, path.relative_to(ROOT)
        assert "alert_email" not in text, path.relative_to(ROOT)


def test_f11_rf_04_nenhum_email_versionado() -> None:
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
