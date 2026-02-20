from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from kausal_common.deployment import env_bool

if TYPE_CHECKING:
    from types import FrameType


def get_debugger():
    from .debugger import get_debugger_cls
    return get_debugger_cls()()


def init_debugger():
    if not env_bool('KAUSAL_INIT_DEBUGGER', default=False):
        return
    sys.breakpointhook = set_trace


def set_trace(frame: FrameType | None = None):
    if frame is None:
        frame = sys._getframe().f_back
    get_debugger().set_trace(frame)
