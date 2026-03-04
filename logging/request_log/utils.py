from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any
from urllib.parse import parse_qs

from loguru import logger

if TYPE_CHECKING:
    from kausal_common.logging.request_log.models import BaseLoggedRequest


def parse_request_payload(logged_request: BaseLoggedRequest) -> dict[str, Any] | None:
    """
    Parse the payload from a LoggedRequest's raw_request field.

    Supports application/json and application/x-www-form-urlencoded content types.
    Returns None if the body is empty or the content type is unsupported.
    """
    raw = logged_request.raw_request
    parts = raw.split('\r\n\r\n', 1)
    if len(parts) < 2:
        return None

    header_section, body = parts
    if not body:
        return None

    content_type = ''
    for line in header_section.split('\r\n'):
        if line.lower().startswith('content-type:'):
            content_type = line.split(':', 1)[1].strip().lower()
            break

    if content_type.startswith('application/json'):
        try:
            return json.loads(body)
        except json.JSONDecodeError as e:
            logger.error(e)
            return None

    if content_type.startswith('application/x-www-form-urlencoded'):
        try:
            return parse_qs(body, strict_parsing=True)
        except ValueError as e:
            logger.error(e)
            return None
    return None
