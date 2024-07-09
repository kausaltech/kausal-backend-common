import sys
import types
from typing import cast
import warnings

import rich
from rich.traceback import Traceback


console = rich.get_console()


def warn_with_traceback(message, category, filename, lineno, file=None, line=None):
    tb = None
    depth = 2
    while True:
        try:
            frame = sys._getframe(depth)
            depth += 1
        except ValueError:
            break
        tb = types.TracebackType(tb, frame, frame.f_lasti, frame.f_lineno)
    exc = cast(Exception, category(message)).with_traceback(tb)

    tbp = Traceback.from_exception(type(exc), exc, traceback=tb, max_frames=20)
    console.print(tbp)
    return


def register_warning_handler():
    warnings.showwarning = warn_with_traceback
