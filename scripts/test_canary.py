"""Testes da decisão do canário (F02-RF-02: promoção ou rollback automático)."""

from collections.abc import Iterator

import canary as c
import pytest

LIMITS = c.Thresholds(max_5xx_ratio=0.01, max_p95_ms=10_000, min_requests=20)


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds


def _run(
    probes: Iterator[bool], metrics: Iterator[c.Metrics], duration: float = 900
) -> bool:
    clock = FakeClock()
    return c.run(
        probe=lambda: next(probes),
        fetch_metrics=lambda: next(metrics),
        limits=LIMITS,
        duration_s=duration,
        interval_s=60,
        sleep=clock.sleep,
        clock=clock,
        out=lambda _: None,
    )


def _forever(value: object) -> Iterator:  # type: ignore[type-arg]
    while True:
        yield value


@pytest.mark.req("F02-RF-02")
def test_promove_quando_saudavel_durante_toda_a_janela() -> None:
    assert _run(
        _forever(True), _forever(c.Metrics(total=500, errors_5xx=2, p95_ms=800))
    )


@pytest.mark.req("F02-RF-02")
def test_rollback_quando_healthz_falha_duas_vezes_seguidas_em_ate_5_minutos() -> None:
    clock = FakeClock()
    ok = c.run(
        probe=lambda: False,
        fetch_metrics=lambda: c.Metrics(),
        limits=LIMITS,
        duration_s=900,
        interval_s=60,
        sleep=clock.sleep,
        clock=clock,
        out=lambda _: None,
    )
    assert not ok
    assert clock.now <= 300  # AT-F02-03: rollback em menos de 5 minutos


def test_uma_falha_isolada_de_healthz_nao_reprova() -> None:
    probes = iter([True, False, True] + [True] * 20)
    assert _run(probes, _forever(c.Metrics(total=100)))


@pytest.mark.req("F02-RF-02")
def test_rollback_quando_taxa_de_5xx_passa_do_limite() -> None:
    assert not _run(_forever(True), _forever(c.Metrics(total=100, errors_5xx=5)))


def test_rollback_quando_p95_passa_do_limite() -> None:
    assert not _run(_forever(True), _forever(c.Metrics(total=100, p95_ms=12_000)))


def test_poucas_requisicoes_nao_reprovam_por_taxa() -> None:
    assert _run(_forever(True), _forever(c.Metrics(total=5, errors_5xx=5)))


def test_metricas_indisponiveis_nao_reprovam_sozinhas() -> None:
    def broken() -> c.Metrics:
        raise OSError("timeout")

    clock = FakeClock()
    assert c.run(
        probe=lambda: True,
        fetch_metrics=broken,
        limits=LIMITS,
        duration_s=120,
        interval_s=60,
        sleep=clock.sleep,
        clock=clock,
        out=lambda _: None,
    )


def test_parse_request_counts_soma_por_classe() -> None:
    payload = {
        "timeSeries": [
            {
                "metric": {"labels": {"response_code_class": "2xx"}},
                "points": [
                    {"value": {"int64Value": "90"}},
                    {"value": {"int64Value": "5"}},
                ],
            },
            {
                "metric": {"labels": {"response_code_class": "5xx"}},
                "points": [{"value": {"int64Value": "3"}}],
            },
        ]
    }
    assert c.parse_request_counts(payload) == (98, 3)
    assert c.parse_request_counts({}) == (0, 0)


def test_parse_p95_pega_o_maior_ponto() -> None:
    payload = {
        "timeSeries": [
            {
                "points": [
                    {"value": {"doubleValue": 120.5}},
                    {"value": {"doubleValue": 300}},
                ]
            }
        ]
    }
    assert c.parse_p95(payload) == 300
    assert c.parse_p95({"timeSeries": []}) is None


def test_main_exige_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GCP_ACCESS_TOKEN", raising=False)
    args = [
        "--project",
        "p",
        "--service",
        "api",
        "--revision",
        "r",
        "--url",
        "https://x",
    ]
    assert c.main(args) == 2
