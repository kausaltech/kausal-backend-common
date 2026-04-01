from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING

from loguru import logger

from kausal_common.telemetry import init_telemetry

if TYPE_CHECKING:
    from collections.abc import Callable

    from gunicorn.arbiter import Arbiter  # type: ignore[import-not-found]
    from gunicorn.workers.base import Worker


gunicorn_log = logger.bind(name='gunicorn.start')


def _report_to_sentry() -> None:
    with contextlib.suppress(Exception):
        import sentry_sdk

        sentry_sdk.capture_exception()


def _patch_prometheus_master() -> None:
    """
    Monkey-patch PrometheusMaster to work with Gunicorn 24+.

    gunicorn-prometheus-exporter 0.2.4 overrides SIG_QUEUE with a plain list,
    but Gunicorn 24+ expects a queue.SimpleQueue. Patch the two methods that
    touch SIG_QUEUE to use the queue API instead.
    """
    import queue
    import signal

    from gunicorn_prometheus_exporter.master import PrometheusMaster

    _orig_init_signals = PrometheusMaster.init_signals

    def init_signals(self) -> None:
        _orig_init_signals(self)
        if not isinstance(self.SIG_QUEUE, queue.SimpleQueue):
            self.SIG_QUEUE = queue.SimpleQueue()

    def signal_handler(self, sig, frame) -> None:
        if sig == signal.SIGINT:
            # Let the parent Arbiter handle SIGINT for immediate termination
            super(PrometheusMaster, self).signal(sig, frame)
            return
        if self.SIG_QUEUE.qsize() < 5:
            self.SIG_QUEUE.put_nowait(sig)
            self.wakeup()

    PrometheusMaster.init_signals = init_signals
    PrometheusMaster.signal = signal_handler


def _get_prometheus_hooks() -> dict | None:
    try:
        from gunicorn_prometheus_exporter.hooks import (
            default_on_exit,
            default_on_starting,
            default_post_fork,
            default_when_ready,
            default_worker_int,
        )
    except ImportError:
        return None
    try:
        _patch_prometheus_master()
    except Exception:
        gunicorn_log.opt(exception=True).warning('Failed to patch prometheus exporter; disabling')
        _report_to_sentry()
        return None
    return dict(
        on_starting=default_on_starting,
        when_ready=default_when_ready,
        post_fork=default_post_fork,
        worker_int=default_worker_int,
        on_exit=default_on_exit,
    )


def pre_import():
    """Import import some of the larger packages before forking."""

    with contextlib.suppress(ImportError):
        import pandas as pd  # type: ignore[import-untyped]  # noqa: F401

    with contextlib.suppress(ImportError):
        import polars as pl  # noqa: F401

    with contextlib.suppress(ImportError):
        from nodes.units import unit_registry  # type: ignore[import-not-found]  # noqa: F401

    gunicorn_log.info('Additional imports completed')


def _make_when_ready(prom_when_ready: Callable | None) -> Callable:
    def when_ready(server: Arbiter) -> None:
        from kausal_common.deployment import run_deployment_checks

        if prom_when_ready:
            try:
                prom_when_ready(server)
            except Exception:
                gunicorn_log.opt(exception=True).warning('Prometheus exporter failed in when_ready; disabling')
                _report_to_sentry()

        gunicorn_log.info('Server ready')

        settings = server.cfg.settings
        if not settings['preload_app'].value:
            return

        gunicorn_log.info('Running deployment checks')
        run_deployment_checks()
        gunicorn_log.info('Deployment checks completed')

        pre_import()

    return when_ready


def post_worker_init(worker: Worker):
    from django.core.cache import close_caches
    from django.db import connections

    for conn in connections.all(initialized_only=True):
        conn.close()
    close_caches()


def _make_post_fork(prom_post_fork: Callable | None) -> Callable:
    def post_fork(server: Arbiter, worker: Worker) -> None:
        if prom_post_fork:
            try:
                prom_post_fork(server, worker)
            except Exception:
                gunicorn_log.opt(exception=True).warning('Prometheus exporter failed in post_fork')
                _report_to_sentry()
        gunicorn_log.info('Worker with PID %d started' % worker.pid)
        init_telemetry()

    return post_fork


def _child_exit(server: Arbiter, worker: Worker) -> None:
    """Mark a dead worker's metrics so prometheus_client excludes them from 'live*' aggregations."""
    try:
        from prometheus_client import multiprocess

        multiprocess.mark_process_dead(worker.pid)
    except Exception:
        gunicorn_log.opt(exception=True).warning('Failed to mark worker %d as dead in prometheus multiproc' % worker.pid)


def get_gunicorn_hooks():
    prom_hooks = _get_prometheus_hooks() or {}
    hooks = dict(
        when_ready=_make_when_ready(prom_hooks.get('when_ready')),
        post_fork=_make_post_fork(prom_hooks.get('post_fork')),
        post_worker_init=post_worker_init,
        child_exit=_child_exit,
    )
    # Wrap pass-through prometheus hooks so they degrade gracefully.
    # Gunicorn validates hook arity via inspect, so wrappers must match
    # the original signature (1-arg for on_starting/worker_int/on_exit,
    # 2-arg for post_fork).
    for key in ('on_starting', 'worker_int', 'on_exit'):
        if key not in prom_hooks:
            continue
        prom_hook = prom_hooks[key]

        def _make_safe_hook(hook: Callable, name: str) -> Callable:
            def _safe_hook(arg) -> None:
                try:
                    hook(arg)
                except Exception:
                    gunicorn_log.opt(exception=True).warning('Prometheus exporter failed in %s' % name)
                    _report_to_sentry()

            return _safe_hook

        hooks[key] = _make_safe_hook(prom_hook, key)
    return hooks
