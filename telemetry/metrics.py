from __future__ import annotations

import os
import uuid
from typing import TYPE_CHECKING

from opentelemetry import metrics
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import ConsoleMetricExporter, PeriodicExportingMetricReader
from opentelemetry.sdk.metrics.view import View
from opentelemetry.sdk.resources import Resource
from opentelemetry.semconv._incubating.attributes.deployment_attributes import DEPLOYMENT_ENVIRONMENT_NAME
from opentelemetry.semconv.attributes.k8s_attributes import K8S_NAMESPACE_NAME, K8S_POD_NAME
from opentelemetry.semconv.attributes.service_attributes import SERVICE_INSTANCE_ID, SERVICE_NAME, SERVICE_VERSION

from kausal_common.context import get_project_id
from kausal_common.deployment import env_bool, get_deployment_build_id
from kausal_common.deployment.types import get_deployment_environment

if TYPE_CHECKING:
    from opentelemetry.sdk.metrics.export import MetricReader


HEALTH_CHECK_EXCLUDED_URLS = r'/(?:healthz|readyz)/?(?:\?.*)?$'


def init_metrics():
    resource = Resource.create(
        attributes={
            SERVICE_NAME: get_project_id(),
            SERVICE_VERSION: get_deployment_build_id() or 'dev',
            SERVICE_INSTANCE_ID: f'{os.getenv("POD_NAME", "local")}-{uuid.uuid4()}',
            DEPLOYMENT_ENVIRONMENT_NAME: get_deployment_environment().value,
            K8S_NAMESPACE_NAME: os.getenv('POD_NAMESPACE', 'local'),
            K8S_POD_NAME: os.getenv('POD_NAME', 'local'),
        }
    )

    metric_readers: list[MetricReader] = []
    otlp_endpoint = os.getenv('OTEL_EXPORTER_OTLP_METRICS_ENDPOINT')
    if otlp_endpoint:
        metric_readers.append(
            PeriodicExportingMetricReader(
                OTLPMetricExporter(endpoint=otlp_endpoint, timeout=2),
                export_interval_millis=30_000,
                export_timeout_millis=2_000,
            )
        )

    if env_bool('METRICS_DEBUG', default=False):
        metric_readers.append(PeriodicExportingMetricReader(ConsoleMetricExporter()))

    # Django and the outer ASGI middleware observe some of the same requests.
    # Keep their metric streams distinct so Prometheus does not merge them.
    django_meter = 'opentelemetry.instrumentation.django'
    views = [
        View(instrument_name=name, meter_name=django_meter, name=f'django.{name}')
        for name in ('http.server.request.duration', 'http.server.duration', 'http.server.active_requests')
    ]
    provider = MeterProvider(resource=resource, metric_readers=metric_readers, views=views)
    metrics.set_meter_provider(provider)


def init_django_metrics() -> None:
    if not os.getenv('OTEL_EXPORTER_OTLP_METRICS_ENDPOINT'):
        return

    from opentelemetry.instrumentation.django import DjangoInstrumentor
    from opentelemetry.trace import NoOpTracerProvider

    DjangoInstrumentor().instrument(
        tracer_provider=NoOpTracerProvider(),
        excluded_urls=HEALTH_CHECK_EXCLUDED_URLS,
    )
