"""Traces OpenTelemetry → Cloud Trace (F11-RT-02).

Ligado só com `TRACING_ENABLED=true` (prd). Sem isso, a API do OpenTelemetry é no-op e os spans
não custam nada. O span da requisição é o do próprio FastAPI (telemetria nativa), que continua o
trace aberto pelo Cloud Run (`X-Cloud-Trace-Context`, pelo propagador do GCP) com a amostragem
dele; as chamadas httpx (Jira e o modelo no Vertex) e as operações do Firestore viram spans filhos.
"""

import asyncio
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any

from opentelemetry import propagate, trace

TRACER = "specflow"
_configured = False


def configure_tracing(*, enabled: bool, project: str | None, version: str, ratio: float) -> None:
    global _configured
    if not enabled or _configured:
        return
    from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
    from opentelemetry.propagators.cloud_trace_propagator import CloudTraceFormatPropagator
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased

    provider = TracerProvider(
        sampler=ParentBased(TraceIdRatioBased(ratio)),
        resource=Resource.create({"service.name": "specflow-api", "service.version": version}),
    )
    exporter = CloudTraceSpanExporter(project_id=project)  # type: ignore[no-untyped-call]
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    propagate.set_global_textmap(CloudTraceFormatPropagator())
    HTTPXClientInstrumentor().instrument()
    _configured = True


@contextmanager
def span(name: str, **attributes: Any) -> Iterator[None]:
    """Span filho do atual. Use só em trechos sem `yield` no meio (não em geradores)."""
    with trace.get_tracer(TRACER).start_as_current_span(name, attributes=attributes):
        yield


async def in_thread[T](fn: Callable[..., T], *args: Any) -> T:
    """Chamada síncrona ao repositório (Firestore) numa thread, com um span `store.<nome>`."""
    with span(f"store.{getattr(fn, '__name__', 'call')}"):
        return await asyncio.to_thread(fn, *args)
