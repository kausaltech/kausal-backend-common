from __future__ import annotations

import logging
from logging.config import dictConfig
import os
from typing import TYPE_CHECKING, Literal, Protocol

from loguru import logger

from kausal_common.deployment import env_bool

from .handler import LoguruLogger, get_rich_log_console, loguru_logfmt_sink, loguru_rich_sink

if TYPE_CHECKING:
    from logging.config import _DictConfigArgs, _LoggerConfiguration

type LogFormat = Literal['rich', 'logfmt']
type _Level = int | str

class GetHandler(Protocol):
    def __call__(self, level: _Level, handler: str | None = None) -> _LoggerConfiguration: ...


def get_logging_conf(level: GetHandler, log_sql_queries: bool = False):
    config: _DictConfigArgs = {
        'version': 1,
        'disable_existing_loggers': False,
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
            },
            'uwsgi-req': {
                'level': 'DEBUG',
                'class': 'kausal_common.logging.handler.UwsgiReqLogHandler',
            },
        },
        'loggers': {
            'django.db': level('DEBUG' if log_sql_queries else 'INFO'),
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
            '': level('DEBUG'),
        },

    }
    return config


def _init_logging(log_format: LogFormat, log_sql_queries: bool = False) -> GetHandler:
    import sys

    from loguru._colorama import should_colorize

    if log_format == 'logfmt':
        loguru_handlers = [dict(sink=loguru_logfmt_sink, format="{message}")]
    else:
        loguru_handlers = [dict(sink=loguru_rich_sink, format="{message}", colorize=should_colorize(sys.stdout))]

    # This configures loguru
    logger.configure(handlers=loguru_handlers)

    def level(level: _Level, handler: str | None = None) -> _LoggerConfiguration:
        if not handler:
            handlers = ['loguru']
        else:
            handlers = [handler]
        conf: _LoggerConfiguration = dict( # pyright: ignore
            handlers=handlers,
            propagate=False,
            level=level,
        )
        return conf

    if True:
        import warnings

        from wagtail.utils.deprecation import RemovedInWagtail70Warning
        warnings.filterwarnings(action='ignore', category=RemovedInWagtail70Warning)

    logging.setLoggerClass(LoguruLogger)

    if log_format == 'rich':
        from rich.traceback import install

        from .traceback import patch_traceback

        patch_traceback()
        install()

    return level


def _running_in_app_server() -> bool:
    try:
        import uwsgi  # noqa  # type: ignore[import-not-found]
        return True
    except ImportError:
        pass
    if os.getenv('SERVER_SOFTWARE', None):
        return True
    return False

def _should_use_logfmt() -> bool:
    if env_bool('KUBERNETES_LOGGING', default=False) or env_bool('KUBERNETES_MODE', default=False):
        return True

    console = get_rich_log_console()
    if not console.is_terminal or console.is_dumb_terminal:
        return True
    return False

def _autodetect_log_format() -> LogFormat:
    return 'logfmt' if _should_use_logfmt() else 'rich'

def init_logging_django(log_format: LogFormat | None = None, log_sql_queries: bool = False):
    if log_format is None:
        log_format = _autodetect_log_format()
    level: GetHandler = _init_logging(log_format, log_sql_queries=log_sql_queries)
    conf = get_logging_conf(level)
    return conf

def init_logging(log_format: LogFormat | None = None):
    if log_format is None:
        log_format = 'logfmt' if _should_use_logfmt() else 'rich'
    level: GetHandler = _init_logging(log_format)
    conf = get_logging_conf(level)
    dictConfig(conf)
