from __future__ import annotations

import os
import typing
from urllib.parse import urlparse

from django.urls import reverse
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.logging import ignore_logger

from kausal_common.telemetry import otel_enabled

if typing.TYPE_CHECKING:
    from sentry_sdk._types import Event, Hint


def strip_sensitive_cookies(req: dict):
    hdr: dict = req.get('headers', {})
    if not hdr:
        return
    if 'Cookie' in hdr:
        hdr['Cookie'] = '[Filtered]'
    cookies: dict = req.get('cookies') or {}
    remove_cookies: list[str] = []
    for key in cookies.keys():
        lkey = key.lower()
        if 'token' in lkey or 'session' in lkey:
            remove_cookies.append(key)
    for key in remove_cookies:
        if cookies[key]:
            cookies[key] = '[Filtered]'
    return


def before_send_transaction(event: Event, hint: Hint):
    req: dict = event.get('request', None) or {}
    if not req:
        return event

    healthcheck_path = reverse('healthcheck')
    url_string = req.get('url', None)
    if url_string:
        url = urlparse(url_string)
        if url.path == healthcheck_path:
            return None

    strip_sensitive_cookies(req)
    return event


def init_sentry(dsn: str, deployment_type: str, enable_perf_tracing: bool = False):
    sentry_sdk.init(
        dsn=dsn,
        send_default_pii=True,
        traces_sample_rate=1.0,
        profiles_sample_rate=0.1 if enable_perf_tracing else 0.0,
        instrumenter='otel' if otel_enabled() else None,
        integrations=[DjangoIntegration()],
        environment=os.getenv('SENTRY_ENVIRONMENT', None) or deployment_type,
        server_name=os.getenv('NODE_NAME', None),
        before_send_transaction=before_send_transaction,
    )
    ignore_logger('uwsgi-req')
