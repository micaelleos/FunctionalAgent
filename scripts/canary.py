#!/usr/bin/env python3
"""Canário do Cloud Run (F02-RF-02, F02-RT-05; 06-cicd-deploy.md §3).

Observa a revisão candidata enquanto ela recebe uma fração do tráfego e decide se o pipeline
promove (exit 0) ou faz rollback (exit 1). A cada intervalo:

  * chama ``<url da tag>/healthz``; ``--max-health-failures`` falhas seguidas reprovam;
  * consulta o Cloud Monitoring (``run.googleapis.com/request_count`` e
    ``request_latencies``) da revisão desde o início do canário; com pelo menos
    ``--min-requests`` requisições, reprova se 5xx > ``--max-5xx-ratio`` ou p95 > ``--max-p95-ms``.

Só usa a biblioteca padrão. O token de acesso vem de ``GCP_ACCESS_TOKEN``
(``gcloud auth print-access-token``).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime

MONITORING_URL = "https://monitoring.googleapis.com/v3/projects/{project}/timeSeries"


@dataclass(frozen=True)
class Thresholds:
    max_5xx_ratio: float = 0.01
    max_p95_ms: float = 10_000
    min_requests: int = 20
    max_health_failures: int = 2


@dataclass(frozen=True)
class Metrics:
    total: int = 0
    errors_5xx: int = 0
    p95_ms: float | None = None

    @property
    def ratio_5xx(self) -> float:
        return self.errors_5xx / self.total if self.total else 0.0


@dataclass
class State:
    consecutive_health_failures: int = 0
    log: list[str] = field(default_factory=list)


def evaluate(
    state: State, healthy: bool, metrics: Metrics, limits: Thresholds
) -> str | None:
    """Atualiza o estado com uma amostra; devolve o motivo da reprovação ou None."""
    state.consecutive_health_failures = (
        0 if healthy else state.consecutive_health_failures + 1
    )
    if state.consecutive_health_failures >= limits.max_health_failures:
        return f"/healthz falhou {state.consecutive_health_failures} vezes seguidas"
    if metrics.total < limits.min_requests:
        return None
    if metrics.ratio_5xx > limits.max_5xx_ratio:
        return (
            f"taxa de 5xx {metrics.ratio_5xx:.2%} > {limits.max_5xx_ratio:.2%} "
            f"({metrics.errors_5xx}/{metrics.total})"
        )
    if metrics.p95_ms is not None and metrics.p95_ms > limits.max_p95_ms:
        return f"p95 {metrics.p95_ms:.0f} ms > {limits.max_p95_ms:.0f} ms"
    return None


def run(
    *,
    probe: Callable[[], bool],
    fetch_metrics: Callable[[], Metrics],
    limits: Thresholds,
    duration_s: float,
    interval_s: float,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
    out: Callable[[str], None] = print,
) -> bool:
    """Executa o canário; True = promover, False = rollback."""
    state = State()
    deadline = clock() + duration_s
    while True:
        healthy = probe()
        try:
            metrics = fetch_metrics()
        except (
            OSError,
            ValueError,
            KeyError,
        ) as exc:  # métricas indisponíveis não reprovam sozinhas
            out(f"aviso: métricas indisponíveis ({exc})")
            metrics = Metrics()
        reason = evaluate(state, healthy, metrics, limits)
        out(
            f"healthz={'ok' if healthy else 'FALHA'} requisições={metrics.total} "
            f"5xx={metrics.errors_5xx} p95={metrics.p95_ms or '-'}ms"
        )
        if reason:
            out(f"REPROVADO: {reason}")
            return False
        if clock() >= deadline:
            out("APROVADO: canário saudável durante toda a janela")
            return True
        sleep(interval_s)


# ---------------------------------------------------------------- integrações (I/O)


def http_probe(url: str, timeout: float = 5.0) -> Callable[[], bool]:
    def probe() -> bool:
        try:
            with urllib.request.urlopen(url, timeout=timeout) as resp:
                return bool(resp.status == 200)
        except (urllib.error.URLError, TimeoutError, OSError):
            return False

    return probe


def parse_request_counts(payload: dict[str, object]) -> tuple[int, int]:
    """Soma requisições e 5xx de uma resposta timeSeries.list agrupada por response_code_class."""
    total = errors = 0
    for series in payload.get("timeSeries", []) or []:  # type: ignore[union-attr]
        labels = series.get("metric", {}).get("labels", {})
        count = sum(
            int(p["value"].get("int64Value", 0)) for p in series.get("points", [])
        )
        total += count
        if labels.get("response_code_class") == "5xx":
            errors += count
    return total, errors


def parse_p95(payload: dict[str, object]) -> float | None:
    values = [
        float(p["value"]["doubleValue"])
        for series in payload.get("timeSeries", []) or []  # type: ignore[union-attr]
        for p in series.get("points", [])
        if "doubleValue" in p.get("value", {})
    ]
    return max(values) if values else None


def monitoring_fetcher(
    *, project: str, service: str, revision: str, token: str, start: datetime
) -> Callable[[], Metrics]:
    base = MONITORING_URL.format(project=project)
    resource = (
        f'resource.type = "cloud_run_revision" AND resource.labels.service_name = "{service}" '
        f'AND resource.labels.revision_name = "{revision}"'
    )

    def query(metric: str, params: dict[str, str]) -> dict[str, object]:
        now = datetime.now(UTC)
        window = max(60, int((now - start).total_seconds()))
        query_params = {
            "filter": f'metric.type = "{metric}" AND {resource}',
            "interval.startTime": start.isoformat().replace("+00:00", "Z"),
            "interval.endTime": now.isoformat().replace("+00:00", "Z"),
            "aggregation.alignmentPeriod": f"{window}s",
            **params,
        }
        req = urllib.request.Request(
            f"{base}?{urllib.parse.urlencode(query_params)}",
            headers={"Authorization": f"Bearer {token}"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data: dict[str, object] = json.load(resp)
            return data

    def fetch() -> Metrics:
        counts = query(
            "run.googleapis.com/request_count",
            {
                "aggregation.perSeriesAligner": "ALIGN_DELTA",
                "aggregation.crossSeriesReducer": "REDUCE_SUM",
                "aggregation.groupByFields": "metric.label.response_code_class",
            },
        )
        latency = query(
            "run.googleapis.com/request_latencies",
            {
                "aggregation.perSeriesAligner": "ALIGN_DELTA",
                "aggregation.crossSeriesReducer": "REDUCE_PERCENTILE_95",
            },
        )
        total, errors = parse_request_counts(counts)
        return Metrics(total=total, errors_5xx=errors, p95_ms=parse_p95(latency))

    return fetch


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--project", required=True)
    parser.add_argument("--service", required=True)
    parser.add_argument("--revision", required=True, help="nome da revisão candidata")
    parser.add_argument("--url", required=True, help="URL da tag da revisão (rc-<sha>)")
    parser.add_argument(
        "--duration", type=float, default=900, help="segundos (padrão 15 min)"
    )
    parser.add_argument("--interval", type=float, default=60)
    parser.add_argument("--max-5xx-ratio", type=float, default=Thresholds.max_5xx_ratio)
    parser.add_argument("--max-p95-ms", type=float, default=Thresholds.max_p95_ms)
    parser.add_argument("--min-requests", type=int, default=Thresholds.min_requests)
    parser.add_argument(
        "--max-health-failures", type=int, default=Thresholds.max_health_failures
    )
    args = parser.parse_args(argv)

    token = os.environ.get("GCP_ACCESS_TOKEN", "")
    if not token:
        print("GCP_ACCESS_TOKEN não definido", file=sys.stderr)
        return 2
    limits = Thresholds(
        max_5xx_ratio=args.max_5xx_ratio,
        max_p95_ms=args.max_p95_ms,
        min_requests=args.min_requests,
        max_health_failures=args.max_health_failures,
    )
    ok = run(
        probe=http_probe(args.url.rstrip("/") + "/healthz"),
        fetch_metrics=monitoring_fetcher(
            project=args.project,
            service=args.service,
            revision=args.revision,
            token=token,
            start=datetime.now(UTC),
        ),
        limits=limits,
        duration_s=args.duration,
        interval_s=args.interval,
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
