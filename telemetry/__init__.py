from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

from opentelemetry.sdk.resources import SERVICE_NAME, SERVICE_VERSION, Resource

from kausal_common.deployment import env_bool

if TYPE_CHECKING:
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.trace import Span

_otel_initialized = False


def _should_init_otel() -> bool:
    return bool(os.getenv('OTEL_EXPORTER_OTLP_TRACES_ENDPOINT'))


def _get_tracer_provider() -> TracerProvider:
    from opentelemetry.sdk.trace import TracerProvider

    return TracerProvider(
        resource=Resource.create(
            {
                SERVICE_NAME: os.getenv('SENTRY_PROJECT', '').split('@')[0] or 'django',
                SERVICE_VERSION: os.getenv('BUILD_ID', 'dev'),
            },
        ),
    )


def _init_sentry_otel() -> None:
    from opentelemetry import trace
    from opentelemetry.propagate import set_global_textmap
    from sentry_sdk.integrations.opentelemetry.propagator import SentryPropagator
    from sentry_sdk.integrations.opentelemetry.span_processor import SentrySpanProcessor

    provider = _get_tracer_provider()
    provider.add_span_processor(SentrySpanProcessor())
    trace.set_tracer_provider(provider)
    set_global_textmap(SentryPropagator())


def _init_oltp_otel() -> None:
    try:
        from opentelemetry import trace
    except ImportError:
        return

    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.trace.export import (
        BatchSpanProcessor,
        ConsoleSpanExporter,
    )

    provider = _get_tracer_provider()
    oltp_traces_endpoint = os.getenv('OTEL_EXPORTER_OTLP_TRACES_ENDPOINT')
    if oltp_traces_endpoint:
        exporter = OTLPSpanExporter('http://127.0.0.1:4317')
        provider.add_span_processor(
            BatchSpanProcessor(exporter),
        )
    elif env_bool('OTEL_EXPORTER_CONSOLE', default=False):
        provider.add_span_processor(
            BatchSpanProcessor(ConsoleSpanExporter()),
        )

    # Sets the global default tracer provider
    trace.set_tracer_provider(provider)


def init_telemetry() -> None:
    global _otel_initialized  # noqa: PLW0603

    if _otel_initialized:
        return

    oltp_traces_endpoint = os.getenv('OTEL_EXPORTER_OTLP_TRACES_ENDPOINT')
    if not oltp_traces_endpoint:
        _init_sentry_otel()
    else:
        _init_oltp_otel()
    _otel_initialized = True


def redis_request_hook(span: Span, instance, args: tuple[Any, ...], kwargs: dict[str, Any]):
    parts = [str(arg) for arg in args]
    span.update_name(' '.join(parts))


def init_django_telemetry():
    if not otel_enabled():
        return

    from opentelemetry.instrumentation.django import DjangoInstrumentor
    from opentelemetry.instrumentation.psycopg import PsycopgInstrumentor
    from opentelemetry.instrumentation.redis import RedisInstrumentor
    from opentelemetry.instrumentation.threading import ThreadingInstrumentor

    DjangoInstrumentor().instrument()
    ThreadingInstrumentor().instrument()
    PsycopgInstrumentor().instrument(enable_commenter=True)
    RedisInstrumentor().instrument(request_hook=redis_request_hook)


def otel_enabled() -> bool:
    return False
    return _should_init_otel()
