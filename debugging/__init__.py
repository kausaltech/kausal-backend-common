from __future__ import annotations

import sys
import threading
from functools import cache
from typing import TYPE_CHECKING

from kausal_common.deployment import env_bool

if TYPE_CHECKING:
    from pdb import Pdb
    from types import FrameType


@cache
def get_debugger() -> Pdb:
    from .debugger import get_debugger_cls

    return get_debugger_cls()()


def init_debugger() -> None:
    if not env_bool('KAUSAL_INIT_DEBUGGER', default=False):
        return
    if 'debugpy' in sys.modules:
        return
    sys.breakpointhook = set_trace


def set_trace(frame: FrameType | None = None) -> None:
    if 'debugpy' in sys.modules:
        import debugpy  # noqa: T100

        debugpy.breakpoint()  # noqa: T100
        return
    if frame is None:
        frame = sys._getframe().f_back
    get_debugger().set_trace(frame)


def _maybe_debugpy_postmortem(exc: Exception) -> None:
    try:
        import debugpy  # noqa: T100
        import pydevd  # type: ignore
    except ImportError:
        # If pydevd isn't available, no debugger attached; do nothing.
        return

    if not debugpy.is_client_connected():
        return

    py_db = pydevd.get_global_debugger()
    thread = threading.current_thread()
    additional_info = py_db.set_additional_thread_info(thread)
    additional_info.is_tracing += 1
    try:
        py_db.stop_on_unhandled_exception(py_db, thread, additional_info, (type(exc), exc, exc.__traceback__))
    finally:
        additional_info.is_tracing -= 1


def post_mortem(exc: Exception) -> None:
    if 'debugpy' in sys.modules:
        _maybe_debugpy_postmortem(exc)
        return

    get_debugger().interaction(None, exc)


__all__ = ['init_debugger', 'post_mortem', 'set_trace']
