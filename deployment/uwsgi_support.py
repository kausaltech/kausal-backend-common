import contextlib
import os

from uwsgidecorators import postfork


@postfork
def close_conns_post_fork():
    from django.db import connections

    for conn in connections.all():
        conn.close()


@postfork
def register_prometheus_cleanup() -> None:
    """Mark this worker dead in PROMETHEUS_MULTIPROC_DIR on exit so per-PID metric files don't accumulate as workers cycle."""
    if not os.environ.get('PROMETHEUS_MULTIPROC_DIR'):
        return
    try:
        import uwsgi
        from prometheus_client import multiprocess
    except ImportError:
        return
    pid = os.getpid()

    def _mark_dead() -> None:
        with contextlib.suppress(Exception):
            multiprocess.mark_process_dead(pid)

    uwsgi.atexit = _mark_dead
