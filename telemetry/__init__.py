import os
try:
    from opentelemetry import trace
except ImportError:
    trace = None

from kausal_common.deployment import env_bool


def init_telemetry():
    if trace is None:
        return

    from opentelemetry.sdk.resources import SERVICE_NAME, SERVICE_VERSION, Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import (
        BatchSpanProcessor,
        ConsoleSpanExporter,
    )
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

    provider = TracerProvider(
        resource=Resource.create({
            SERVICE_NAME: os.getenv('SENTRY_PROJECT', '').split('@')[0] or 'django',
            SERVICE_VERSION: os.getenv('BUILD_ID', 'dev'),
        }),
    )
    oltp_traces_endpoint = os.getenv('OTEL_EXPORTER_OTLP_TRACES_ENDPOINT')
    if oltp_traces_endpoint:
        exporter = OTLPSpanExporter('http://127.0.0.1:4317')
        provider.add_span_processor(
            BatchSpanProcessor(exporter)
        )
    elif env_bool('OTEL_EXPORTER_CONSOLE', False):
        provider.add_span_processor(
            BatchSpanProcessor(ConsoleSpanExporter())
        )

    # Sets the global default tracer provider
    trace.set_tracer_provider(provider)


def init_django_telemetry():
    if not otel_enabled():
        return

    from opentelemetry.instrumentation.django import DjangoInstrumentor

    init_telemetry()
    DjangoInstrumentor().instrument()


def otel_enabled() -> bool:
    return trace is not None
