from __future__ import annotations

import sys
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


def init_debugger():
    if not env_bool('KAUSAL_INIT_DEBUGGER', default=False):
        return
    sys.breakpointhook = set_trace


def set_trace(frame: FrameType | None = None):
    if frame is None:
        frame = sys._getframe().f_back
    get_debugger().set_trace(frame)


def post_mortem(exc: Exception) -> None:
    get_debugger().interaction(None, exc)


__all__ = ['init_debugger', 'post_mortem', 'set_trace']
