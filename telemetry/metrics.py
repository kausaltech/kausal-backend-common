from __future__ import annotations

import os

from opentelemetry import metrics
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import ConsoleMetricExporter, MetricReader, PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.semconv._incubating.attributes.deployment_attributes import DEPLOYMENT_ENVIRONMENT_NAME
from opentelemetry.semconv.attributes.service_attributes import SERVICE_NAME, SERVICE_VERSION
from prometheus_client import start_http_server

from kausal_common.context import get_project_id
from kausal_common.deployment import env_bool, get_deployment_build_id
from kausal_common.deployment.types import get_deployment_environment


def init_metrics():
    resource = Resource.create(attributes={
        SERVICE_NAME: get_project_id(),
        SERVICE_VERSION: get_deployment_build_id() or 'dev',
        DEPLOYMENT_ENVIRONMENT_NAME: str(get_deployment_environment()),
    })

    metric_readers: list[MetricReader] = []
    prometheus_port = os.getenv('METRICS_PORT', None)
    if prometheus_port:
        prom_reader = PrometheusMetricReader()
        start_http_server(port=int(prometheus_port))
        metric_readers.append(prom_reader)

    if env_bool('METRICS_DEBUG', default=False):
        metric_readers.append(PeriodicExportingMetricReader(ConsoleMetricExporter()))

    provider = MeterProvider(resource=resource, metric_readers=metric_readers)
    metrics.set_meter_provider(provider)
