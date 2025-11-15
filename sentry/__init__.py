from __future__ import annotations

from typing_extensions import Any

import sentry_sdk
from loguru import logger


def report_error(message: str, **extra: Any) -> None:
    sentry_sdk.capture_message(message, level="error", **extra)
    logger.error(message, **extra)
