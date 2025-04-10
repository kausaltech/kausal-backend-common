from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from kausal_common.deployment.types import LoggedHttpRequest


@contextmanager
def start_request(request: LoggedHttpRequest):
    log_context = {
        'correlation_id': request.correlation_id,
    }
    if request.client_ip:
        log_context['client_ip'] = request.client_ip
    with logger.contextualize(**log_context):
        yield
