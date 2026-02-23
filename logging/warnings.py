from __future__ import annotations

import sys
import types
import warnings
from typing import TextIO

import rich
from rich.traceback import Traceback

from kausal_common.deployment import env_bool

console = rich.get_console()

_warning_traceback_enabled = False


IGNORE_WARNINGS = [
    "Core Pydantic V1 functionality isn't compatible with Python 3.14 or greater.",
    "Defining `exclude_fields` is deprecated in favour of `exclude`.",
]

IGNORE_WARNINGS_STARTSWITH = [
    "Creating a DjangoObjectType without either the `fields` or the `exclude` option is deprecated. Add an explicit ",
    "pkg_resources is deprecated as an API",
    "'asyncio.iscoroutinefunction' is deprecated",
]


def warn_with_traceback(
    message: Warning | str,
    category: type[Warning],
    filename: str,  # pyright: ignore[reportUnusedParameter]
    lineno: int,  # pyright: ignore[reportUnusedParameter]
    file: TextIO | None = None,  # pyright: ignore[reportUnusedParameter]
    line: str | None = None,  # pyright: ignore[reportUnusedParameter]
) -> None:
    tb = None
    depth = 2
    msg_str = str(message)
    if msg_str in IGNORE_WARNINGS:
        return
    if any(msg_str.startswith(prefix) for prefix in IGNORE_WARNINGS_STARTSWITH):
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
