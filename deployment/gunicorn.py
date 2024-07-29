from __future__ import annotations

from typing import TYPE_CHECKING
from loguru import logger

from kausal_common.telemetry import init_telemetry

if TYPE_CHECKING:
    from gunicorn.arbiter import Arbiter
    from gunicorn.workers.base import Worker


gunicorn_log = logger.bind(name='gunicorn.start')


def when_ready(server: Arbiter):
    from kausal_common.deployment import run_deployment_checks

    gunicorn_log.info('Server ready')

    settings = server.cfg.settings
    if settings['preload_app'].value:
        gunicorn_log.info('Running deployment checks')
        run_deployment_checks()
        gunicorn_log.info('Deployment checks completed')


def post_fork(server: Arbiter, worker: Worker):
    gunicorn_log.info('Worker with PID %d started' % worker.pid)
    init_telemetry()


def get_gunicorn_hooks():
    return dict(
        when_ready=when_ready,
        post_fork=post_fork,
    )
