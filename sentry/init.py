from __future__ import annotations

import contextlib
import os
from functools import wraps
from typing import TYPE_CHECKING, cast
from urllib.parse import urlparse

from django.urls import reverse

import sentry_sdk
import sentry_sdk.integrations
from sentry_sdk.consts import DEFAULT_MAX_VALUE_LENGTH

from kausal_common.context import get_project_id
from kausal_common.deployment import coerce_bool, env_bool
from kausal_common.deployment.types import is_development_environment
from kausal_common.telemetry.traces import init_django_telemetry, otel_traces_enabled

if TYPE_CHECKING:
    from collections.abc import Callable

    from sentry_sdk._types import Event, Hint
    from sentry_sdk.consts import Experiments
    from sentry_sdk.envelope import Envelope
    from sentry_sdk.integrations import Integration


def strip_sensitive_cookies(req: dict):
    hdr: dict = req.get('headers', {})
    if not hdr:
        return
    if 'Cookie' in hdr:
        hdr['Cookie'] = '[Filtered]'
    cookies: dict = req.get('cookies') or {}
    remove_cookies: list[str] = []
    for key in cookies:
        lkey = key.lower()
        if 'token' in lkey or 'session' in lkey:
            remove_cookies.append(key)
    for key in remove_cookies:
        if cookies[key]:
            cookies[key] = '[Filtered]'
    return


_in_interactive_mode: bool | None = None


def suppress_send(value: bool):
    global _in_interactive_mode  # noqa: PLW0603
    _in_interactive_mode = value


def is_in_interactive_mode():
    global _in_interactive_mode  # noqa: PLW0603
    if _in_interactive_mode is not None:
        return _in_interactive_mode

    try:
        get_ipython().__class__.__name__  # type: ignore  # noqa: B018, F821
    except Exception:
        _in_interactive_mode = False
    else:
        _in_interactive_mode = True
    return _in_interactive_mode


def before_send_transaction(event: Event, hint: Hint):
    from kausal_common.deployment.health_check_view import HEALTH_CHECK_VIEW_NAME

    if is_in_interactive_mode():
        return None

    req: dict = event.get('request', None) or {}
    if not req:
        return event

    exclude_paths: list[str] = []

    with contextlib.suppress(Exception):
        exclude_paths.append(reverse(HEALTH_CHECK_VIEW_NAME))

    url_string = req.get('url')
    if url_string:
        url = urlparse(url_string)
        if url.path in exclude_paths:
            return None

    strip_sensitive_cookies(req)
    return event


def before_send(event: Event, hint: Hint):
    if is_in_interactive_mode():
        return None
    return event


def _get_spotlight_url() -> str | None:
    from sentry_sdk.spotlight import DEFAULT_SPOTLIGHT_URL

    if not is_development_environment() and not env_bool('SENTRY_SPOTLIGHT_FORCE', default=False):
        return None

    spotlight_env = os.getenv('SENTRY_SPOTLIGHT', None)
    if spotlight_env is None:
        return None
    enabled = coerce_bool(spotlight_env)
    if enabled is None:
        return spotlight_env
    return DEFAULT_SPOTLIGHT_URL if enabled else None


def is_spotlight_enabled() -> bool:
    return _get_spotlight_url() is not None


def _wrap_method[F: Callable](func: F, op: str, get_desc: Callable | None = None) -> F:
    if getattr(func, '_sentry_wrapped', False):
        return func

    @wraps(func)
    def wrap_with_span(*args, **kwargs):  # noqa: ANN202
        if get_desc is not None:
            desc = get_desc(*args, **kwargs)
        else:
            desc = None
        with sentry_sdk.start_span(op=op, name=desc):
            return func(*args, **kwargs)

    setattr(wrap_with_span, '_sentry_wrapped', True)  # noqa: B010
    return cast('F', wrap_with_span)


def _patch_django_init() -> None:
    from django.apps.config import AppConfig
    from django.apps.registry import apps

    def get_app_label(*args, **kwargs):  # noqa: ANN202
        return args[0]

    def get_self_app(self):  # noqa: ANN202
        return self.name

    apps.populate = _wrap_method(apps.populate, op='populate apps')  # type: ignore[method-assign]
    AppConfig.create = _wrap_method(AppConfig.create, op='create appconfig', get_desc=get_app_label)  # type: ignore[method-assign]
    AppConfig.import_models = _wrap_method(AppConfig.import_models, op='import models', get_desc=get_self_app)  # type: ignore[method-assign]


class NullTransport(sentry_sdk.Transport):
    def capture_envelope(self, envelope: Envelope):
        client = sentry_sdk.get_client()
        if not client.spotlight:
            return
        has_non_log_items = False
        for item in envelope.items:
            if item.type != 'log':
                has_non_log_items = True
                break
        if has_non_log_items:
            return
        client.spotlight.capture_envelope(envelope)


DISABLED_DEFAULT_INTEGRATIONS = {'modules', 'argv', 'loguru', 'logging', 'graphene', 'strawberry', 'aiohttp', 'gql', 'tornado'}

def _get_integrations() -> list[Integration]:
    from django.db.models.signals import post_init, pre_init

    from sentry_sdk.integrations import iter_default_integrations
    from sentry_sdk.integrations.boto3 import Boto3Integration
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.redis import RedisIntegration

    integrations: list[Integration] = []
    for integration_cls in iter_default_integrations(False):  # noqa: FBT003
        if integration_cls.identifier in DISABLED_DEFAULT_INTEGRATIONS:
            continue
        integration = integration_cls()
        integrations.append(integration)
    integrations.append(DjangoIntegration(
        middleware_spans=False,
        signals_denylist=[pre_init, post_init]
    ))
    integrations.append(Boto3Integration())
    integrations.append(CeleryIntegration())
    integrations.append(RedisIntegration())
    return integrations


def init_sentry(dsn: str | None, deployment_type: str | None = None):
    from kausal_common.telemetry import init_telemetry

    if sentry_sdk.is_initialized():
        return
    spotlight_url = _get_spotlight_url()
    if spotlight_url and not dsn:
        # We need to set a DSN to enable spotlight
        dsn = 'http://abcd@localhost/1'
        transport = NullTransport()
    else:
        transport = None

    if spotlight_url:
        from rich import print

        spotlight_view_url = spotlight_url.removesuffix('/stream')
        print(f'🔦 Spotlight enabled at: [link={spotlight_view_url}]{spotlight_view_url}')

    if is_development_environment() and not os.getenv('SENTRY_RELEASE'):
        release = '%s@dev' % get_project_id()
    else:
        release = None

    integrations = _get_integrations()

    experiments: Experiments = {"transport_http2": not bool(spotlight_url)}
    if is_spotlight_enabled():
        experiments['enable_logs'] = is_spotlight_enabled()

    sentry_sdk.init(
        dsn=dsn,
        debug=env_bool('SENTRY_DEBUG', default=False),
        spotlight=spotlight_url,
        transport=transport,
        send_default_pii=True,
        traces_sample_rate=1.0,
        profiles_sample_rate=1.0 if env_bool('SENTRY_PROFILING', default=False) else 0.0,
        instrumenter='otel' if otel_traces_enabled() else None,
        release=release,
        integrations=integrations,
        default_integrations=False,
        environment=os.getenv('SENTRY_ENVIRONMENT', None) or deployment_type,
        server_name=os.getenv('NODE_NAME', None),
        before_send_transaction=before_send_transaction,
        before_send=before_send,
        max_value_length=4096 if spotlight_url else DEFAULT_MAX_VALUE_LENGTH,
        max_request_body_size='always' if spotlight_url else 'medium',
        _experiments=experiments,
    )
    if env_bool('SENTRY_TRACE_DJANGO_INIT', default=False):
        _patch_django_init()

    init_telemetry()
    init_django_telemetry()
