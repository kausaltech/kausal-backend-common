from __future__ import annotations

import logging
import re
from typing import Pattern


class BaseFilter(logging.Filter):
    REGEXP_WITHOUT_MATCHES = 'a^'
    match_regexp: Pattern[str]

    def __init__(self, match_str_prefix: str | None = None, **kwargs):
        super().__init__(**kwargs)
        if match_str_prefix is None:
            self.match_regexp = re.compile(self.REGEXP_WITHOUT_MATCHES)
        else:
            self.match_regexp = re.compile(f'^{match_str_prefix}.*$')

    def _match(self, request_path: str | None) -> bool:
        if request_path is None:
            return False
        return self.match_regexp.match(request_path) is not None


class SkipDjangoMatchingPathsFilter(BaseFilter):
    """
    Logging filter to skip logging of specific kinds of requests.

    Mostly intended for reducing noise from static and media files.
    """

    def __init__(
        self,
        match_str_prefix: str | None = None,
        filter_broken_pipe: bool = False,
        **kwargs,
    ):
        self.filter_broken_pipe = filter_broken_pipe
        if match_str_prefix is None:
            super().__init__(**kwargs)
        match_str_prefix=f'"GET {match_str_prefix}'
        super().__init__(match_str_prefix, **kwargs)

    def filter(self, record: logging.LogRecord) -> bool:
        if record.name != 'django.server':
            return True
        message = record.getMessage()
        if self.filter_broken_pipe is True and message.startswith('- Broken pipe from '):
            return False
        if self._match(message):
            return False
        return True


class SkipDjangoMatchingPathsErrorLogFilter(BaseFilter):
    """
    Logging filter to skip logging of specific kinds of exceptional cases.

    Intended for reducing noise from eg. missing media files.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        if record.name != 'django.request':
            return True
        if getattr(record, 'status_code', None) == 200:
            return True
        args = record.args
        request_path = None
        if isinstance(args, tuple) and len(args) > 1:
            request_path = str(args[1])
        if self._match(request_path):
            return False
        return True
