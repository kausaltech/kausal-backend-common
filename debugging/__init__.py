from __future__ import annotations

import sys
import threading
from functools import cache
from typing import TYPE_CHECKING, Any

from kausal_common.deployment import env_bool

if TYPE_CHECKING:
    from pdb import Pdb
    from types import FrameType, TracebackType


@cache
def get_debugger() -> Pdb:
    from .debugger import get_debugger_cls

    return get_debugger_cls()()


def _post_mortem_excepthook(
    _exc_type: type[BaseException],
    exc_value: BaseException,
    _exc_traceback: TracebackType | None,
) -> Any:
    post_mortem(exc_value)


def _post_mortem_threading_excepthook(args: threading.ExceptHookArgs) -> Any:
    if args.exc_value is not None:
        post_mortem(args.exc_value)
    else:
        set_trace()


def init_debugger() -> None:
    if not env_bool('INIT_DEBUGGER', default=False) or 'debugpy' in sys.modules:
        return
    sys.breakpointhook = set_trace
    if env_bool('DEBUG_EXCEPTIONS', default=False):
        sys.excepthook = _post_mortem_excepthook
        threading.excepthook = _post_mortem_threading_excepthook


def set_trace(frame: FrameType | None = None) -> None:
    if 'debugpy' in sys.modules:
        import debugpy  # noqa: T100

        debugpy.breakpoint()  # noqa: T100
        return
    if frame is None:
        frame = sys._getframe().f_back
    get_debugger().set_trace(frame)


def _maybe_debugpy_postmortem(exc: BaseException) -> None:
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


def post_mortem(exc: BaseException) -> None:
    if 'debugpy' in sys.modules:
        _maybe_debugpy_postmortem(exc)
        return

    dbg = get_debugger()
    dbg.reset()
    dbg.interaction(None, exc)


__all__ = ['init_debugger', 'post_mortem', 'set_trace']
