from __future__ import annotations

import contextlib
import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import sentry_sdk

if TYPE_CHECKING:
    from logging import LogRecord


def _breadcrumb_from_record(record: LogRecord) -> dict[str, Any]:
    from sentry_sdk.integrations.logging import LOGGING_TO_EVENT_LEVEL

    return {
        'type': 'log',
        'level': LOGGING_TO_EVENT_LEVEL.get(record.levelno, record.levelname.lower() if record.levelname else ""),
        'category': record.name,
        'message': record.getMessage(),
        'timestamp': datetime.fromtimestamp(record.created, UTC),
        'data': record.exc_info,
    }


def handle_log_record(record: LogRecord) -> None:
    """Generate Sentry breadcrumbs from log records."""

    if record.levelno < logging.INFO:
        return

    with contextlib.suppress(Exception):
        sentry_sdk.add_breadcrumb(_breadcrumb_from_record(record))
