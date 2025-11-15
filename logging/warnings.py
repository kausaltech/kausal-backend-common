from __future__ import annotations

import sys
import types
import warnings
from typing import TextIO, cast

import rich
from rich.traceback import Traceback

from kausal_common.deployment import env_bool

console = rich.get_console()

_warning_traceback_enabled = False


IGNORE_WARNINGS = [
    "Core Pydantic V1 functionality isn't compatible with Python 3.14 or greater.",
]


def warn_with_traceback(
    message: Warning | str,
    category: type[Warning],
    filename: str,
    lineno: int,
    file: TextIO | None = None,
    line: str | None = None,
) -> None:
    tb = None
    depth = 2
    if str(message) in IGNORE_WARNINGS:
        return
    while True:
        try:
            frame = sys._getframe(depth)
            depth += 1
        except ValueError:
            break
        tb = types.TracebackType(tb, frame, frame.f_lasti, frame.f_lineno)

    if isinstance(message, str):
        exc = category(message).with_traceback(tb)
    else:
        exc = message.with_traceback(tb)

    tbp = Traceback.from_exception(type(exc), exc, traceback=tb, max_frames=100)
    console.print(tbp)


def warning_traceback_enabled() -> bool:
    return env_bool('LOG_WARNING_TRACEBACK', default=True)


def register_warning_handler():
    global _warning_traceback_enabled  # noqa: PLW0603

    if not warning_traceback_enabled() or _warning_traceback_enabled:
        return
    _warning_traceback_enabled = True
    warnings.showwarning = warn_with_traceback
