from __future__ import annotations

import contextlib
import os
from functools import wraps
from typing import TYPE_CHECKING, cast
from urllib.parse import urlparse

from django.urls import reverse

import sentry_sdk
import sentry_sdk.integrations
from sentry_sdk.integrations.argv import ArgvIntegration
from sentry_sdk.integrations.django import DjangoIntegration

from kausal_common.deployment import env_bool
from kausal_common.deployment.types import is_development_environment
from kausal_common.telemetry import otel_enabled

if TYPE_CHECKING:
    from collections.abc import Callable

    from sentry_sdk._types import Event, Hint


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

def is_in_interactive_mode():
    global _in_interactive_mode  # noqa: PLW0603
    if _in_interactive_mode is not None:
        return None

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


def _should_enable_spotlight() -> bool:
    # from sentry_sdk.spotlight import DEFAULT_SPOTLIGHT_URL
    # FIXME: Should we try to connect to the default URL?
    if not is_development_environment():
        return False
    return True

def _wrap_method[F: Callable](func: F, op: str, get_desc: Callable | None = None) -> F:
    if getattr(func, '_sentry_wrapped', False):
        return func
    @wraps(func)
    def wrap_with_span(*args, **kwargs):  # noqa: ANN202
        if get_desc is not None:
            desc = get_desc(*args, **kwargs)
        else:
            desc = None
        with sentry_sdk.start_span(op=op, description=desc):
            return func(*args, **kwargs)
    setattr(wrap_with_span, '_sentry_wrapped', True)  # noqa: B010
    return cast(F, wrap_with_span)


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


def init_sentry(dsn: str | None, deployment_type: str | None = None):
    from sentry_sdk.integrations.modules import ModulesIntegration
    if sentry_sdk.is_initialized():
        return
    sentry_sdk.init(
        dsn=dsn,
        debug=env_bool('SENTRY_DEBUG', default=False),
        send_default_pii=True,
        traces_sample_rate=1.0,
        profiles_sample_rate=1.0 if env_bool('SENTRY_PROFILING', default=False) else 0.0,
        instrumenter='otel' if otel_enabled() else None,
        integrations=[DjangoIntegration(
            middleware_spans=False,
        )],
        disabled_integrations=[
            ModulesIntegration(),
            ArgvIntegration(),
        ],
        auto_enabling_integrations=False,
        environment=os.getenv('SENTRY_ENVIRONMENT', None) or deployment_type,
        server_name=os.getenv('NODE_NAME', None),
        before_send_transaction=before_send_transaction,
        before_send=before_send,
        spotlight=_should_enable_spotlight(),
    )
    if env_bool('SENTRY_TRACE_DJANGO_INIT', default=False):
        _patch_django_init()
