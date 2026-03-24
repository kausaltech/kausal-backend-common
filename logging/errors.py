from __future__ import annotations

from typing import TYPE_CHECKING, Any

from loguru import logger
from sentry_sdk import capture_exception, capture_message

if TYPE_CHECKING:
    from sentry_sdk._types import LogLevelStr


def capture_error(
    msg: str,
    level: LogLevelStr = 'error',
    exc: Exception | None = None,
    extras: dict[str, Any] | None = None,
    contexts: dict[str, dict[str, Any]] | None = None,
):
    if exc is not None:
        capture_exception(exc, level=level, extras=extras, contexts=contexts)
    else:
        capture_message(msg, level='error')
    log = logger.opt(depth=1)

    if exc is not None:
        log = log.opt(exception=(type(exc), exc, exc.__traceback__))

    match level:
        case 'debug':
            log_msg = log.debug
        case 'info':
            log_msg = log.info
        case 'warning':
            log_msg = log.warning
        case 'error':
            log_msg = log.error
        case 'critical' | 'fatal':
            log_msg = log.critical
    kwargs: dict[str, Any] = {}
    if extras:
        kwargs.update(extras)
    if contexts:
        kwargs.update(contexts)
    log_msg(msg, **kwargs)


__all__ = ['capture_error']
