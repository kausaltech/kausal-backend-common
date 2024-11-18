from __future__ import annotations

import logging
import warnings
from dataclasses import dataclass
from logging.config import dictConfig
from typing import TYPE_CHECKING, Any, Literal, Protocol

from django.conf import settings

from loguru import logger

from kausal_common.deployment import env_bool
from kausal_common.logging.warnings import register_warning_handler, warning_traceback_enabled

from .handler import LoguruLogger, get_rich_log_console, loguru_logfmt_sink, loguru_rich_sink

if TYPE_CHECKING:
    from logging.config import _DictConfigArgs, _LoggerConfiguration

type LogFormat = Literal['rich', 'logfmt']
type _Level = int | str


class GetHandler(Protocol):
    def __call__(self, level: _Level, handler: str | None = None) -> _LoggerConfiguration: ...


@dataclass
class UserLoggingOptions:
    """Allow developers to add useful debug info and filter extra noise in their local environments."""

    sql_queries: bool = False
    people_verbose: bool = True
    django_runserver_minimize_noise: bool = False
    django_runserver_requests_media: bool = True
    django_runserver_requests_static: bool = True
    django_runserver_requests_favicon: bool = True
    django_runserver_errors_media: bool = True
    django_runserver_errors_static: bool = True
    django_runserver_errors_favicon: bool = True
    django_runserver_requests_broken_pipe: bool = True

    def __post_init__(self):
        if not self.django_runserver_minimize_noise:
            return
        self.django_runserver_requests_media = False
        self.django_runserver_requests_static = False
        self.django_runserver_requests_favicon = False
        self.django_runserver_errors_media = False
        self.django_runserver_errors_favicon = False
        self.django_runserver_requests_broken_pipe = False
        # static errors might indicate bugs
        self.django_runserver_errors_static = True


def get_logging_conf(
    level: GetHandler,
    options: UserLoggingOptions,
):
    filters = _get_filters(options)
    config: _DictConfigArgs = {
        'version': 1,
        'disable_existing_loggers': False,
        'filters': filters,
        'formatters': {
            'verbose': {
                'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s',
            },
            'simple': {
                'format': '%(levelname)s %(name)s %(asctime)s %(message)s',
            },
            'plain': {
                'format': '%(message)s',
            },
        },
        'handlers': {
            'null': {
                'level': 'DEBUG',
                'class': 'logging.NullHandler',
            },
            'console': {
                'level': 'DEBUG',
                'class': 'logging.StreamHandler',
                'formatter': 'simple',
            },
            'loguru': {
                'level': 'DEBUG',
                'class': 'kausal_common.logging.handler.LoguruLoggingHandler',
                'formatter': 'plain',
                'filters': filters.keys(),
            },
            'uwsgi-req': {
                'level': 'DEBUG',
                'class': 'kausal_common.logging.handler.UwsgiReqLogHandler',
            },
        },
        'loggers': {
            'django.db': level('DEBUG' if options.sql_queries else 'INFO'),
            'django.template': level('WARNING'),
            'django.utils.autoreload': level('INFO'),
            'django': level('DEBUG'),
            'environ': level('INFO'),
            'blib2to3': level('INFO'),
            'generic': level('DEBUG'),
            'parso': level('WARNING'),
            'requests': level('WARNING'),
            'urllib3.connectionpool': level('INFO'),
            'elasticsearch': level('WARNING'),
            'PIL': level('INFO'),
            'faker': level('INFO'),
            'factory': level('INFO'),
            'watchfiles': level('INFO'),
            'watchdog': level('INFO'),
            'uwsgi-req': level('DEBUG', handler='uwsgi-req'),
            'git': level('INFO'),
            'pint': level('INFO'),
            'matplotlib': level('INFO'),
            'numba': level('INFO'),
            'botocore': level('INFO'),
            'filelock': level('INFO'),
            'sentry_sdk.errors': level('INFO'),
            'markdown_it': level('INFO'),
            'colormath': level('INFO'),
            'gql': level('WARNING'),
            'psycopg': level('INFO'),
            'aiobotocore': level('INFO'),
            's3fs': level('INFO'),
            'celery.utils': level('INFO'),
            'inotify': level('INFO'),
            'fsspec': level('INFO'),
            'oauthlib.oauth2.rfc6749.endpoints': level('INFO'),
            'people.models': level('INFO' if options.people_verbose else 'WARNING'),
            '': level('DEBUG'),
        },
    }
    return config


def _get_filters(options: UserLoggingOptions) -> dict[str, Any]:
    filters: dict[str, Any] = {}
    for key, substring in (
        ('django_runserver_requests_media', settings.MEDIA_URL),
        ('django_runserver_requests_static', settings.STATIC_URL),
        ('django_runserver_requests_favicon', '/favicon.ico'),
    ):
        if getattr(options, key, True):
            continue
        filters[key] = {
            '()': 'kausal_common.logging.filters.SkipDjangoMatchingPathsFilter',
            'filter_broken_pipe': options.django_runserver_requests_broken_pipe is False,
            'match_str_prefix': substring,
        }

    for key, substring in (
        ('django_runserver_errors_media', settings.MEDIA_URL),
        ('django_runserver_errors_static', settings.STATIC_URL),
        ('django_runserver_errors_favicon', '/favicon.ico'),
    ):
        if getattr(options, key, True):
            continue
        filters[key] = {
            '()': 'kausal_common.logging.filters.SkipDjangoMatchingPathsErrorLogFilter',
            'match_str_prefix': substring,
        }
    return filters


def _init_logging(log_format: LogFormat) -> GetHandler:
    import sys

    from loguru._colorama import should_colorize

    if log_format == 'logfmt':
        loguru_handlers = [dict(sink=loguru_logfmt_sink, format='{message}')]
    else:
        loguru_handlers = [dict(sink=loguru_rich_sink, format='{message}', colorize=should_colorize(sys.stdout))]

    # This configures loguru
    logger.configure(handlers=loguru_handlers)

    def level(level: _Level, handler: str | None = None) -> _LoggerConfiguration:
        if not handler:
            handlers = ['loguru']
        else:
            handlers = [handler]
        conf: _LoggerConfiguration = dict(  # pyright: ignore
            handlers=handlers,
            propagate=False,
            level=level,
        )
        return conf

    if True:
        import warnings

        from wagtail.utils.deprecation import RemovedInWagtail70Warning

        warnings.filterwarnings(action='ignore', category=RemovedInWagtail70Warning)

    if warning_traceback_enabled():
        register_warning_handler()

    logging.setLoggerClass(LoguruLogger)

    if log_format == 'rich':
        from rich.traceback import install

        from .traceback import patch_traceback

        patch_traceback()
        install()

    return level


def _should_use_logfmt() -> bool:
    if env_bool('KUBERNETES_LOGGING', default=False) or env_bool('KUBERNETES_MODE', default=False):
        return True

    console = get_rich_log_console()
    if not console.is_terminal or console.is_dumb_terminal:
        return True
    return False


def _autodetect_log_format() -> LogFormat:
    return 'logfmt' if _should_use_logfmt() else 'rich'


def init_logging_django(
    log_format: LogFormat | None = None,
    log_sql_queries: bool | None = None,
    options: UserLoggingOptions | None = None,
):
    if log_format is None:
        log_format = _autodetect_log_format()
    level: GetHandler = _init_logging(log_format)
    if options is None:
        options = UserLoggingOptions()
    if log_sql_queries is not None:
        warnings.warn(
            'Parameter log_sql_queries is deprecated. Please use the options parameter instead.', DeprecationWarning, stacklevel=2
        )
        options.sql_queries = log_sql_queries

    conf = get_logging_conf(level, options)
    return conf


def init_logging(
    log_format: LogFormat | None = None,
    options: UserLoggingOptions | None = None,
):
    if log_format is None:
        fmt = 'logfmt' if _should_use_logfmt() else 'rich'
    else:
        fmt = log_format
    level: GetHandler = _init_logging(fmt)
    if options is None:
        options = UserLoggingOptions()
    conf = get_logging_conf(level, options)
    dictConfig(conf)
