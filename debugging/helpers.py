import inspect


def hide_from_traceback():
    """Instruct tools to omit the current frame from the stacktrace."""

    frame = inspect.currentframe()
    if frame is None:
        return
    caller = frame.f_back
    if caller is None:
        return
    caller.f_locals['_rich_traceback_omit'] = True
    caller.f_locals['__traceback_hide__'] = True
    caller.f_locals['__tracebackhide__'] = True
