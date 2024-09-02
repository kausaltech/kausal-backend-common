from __future__ import annotations

import contextlib
import gc
import os
from threading import Thread
from typing import TYPE_CHECKING

from loguru import logger

from kausal_common.telemetry import init_telemetry

if TYPE_CHECKING:
    from gunicorn.arbiter import Arbiter
    from gunicorn.workers.base import Worker


gunicorn_log = logger.bind(name='gunicorn.start')


def pre_import():
    """Import import some of the larger packages before forking."""

    with contextlib.suppress(ImportError):
        import pandas as pd  # noqa: F401

    with contextlib.suppress(ImportError):
        import polars as pl  # noqa: F401

    with contextlib.suppress(ImportError):
        from nodes.units import unit_registry  # noqa: F401

    gunicorn_log.info("Additional imports completed")


def when_ready(server: Arbiter):
    from kausal_common.deployment import run_deployment_checks

    gunicorn_log.info('Server ready')

    settings = server.cfg.settings
    if not settings['preload_app'].value:
        return

    gunicorn_log.info('Running deployment checks')
    run_deployment_checks()
    gunicorn_log.info('Deployment checks completed')

    pre_import()


def post_worker_init(worker: Worker):
    from django.core.cache import close_caches
    from django.db import connections

    for conn in connections.all(initialized_only=True):
        conn.close()
    close_caches()


def post_fork(server: Arbiter, worker: Worker):
    gunicorn_log.info('Worker with PID %d started' % worker.pid)
    init_telemetry()


def get_gunicorn_hooks():
    return dict(
        when_ready=when_ready,
        post_fork=post_fork,
        post_worker_init=post_worker_init,
    )
