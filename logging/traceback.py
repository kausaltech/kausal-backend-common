from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

from rich.text import Text
from rich.traceback import Stack, Traceback

if TYPE_CHECKING:
    from rich.console import Group

old_render_stack = Traceback._render_stack
_is_patched = False

FILENAME_LINE = re.compile(r'^(.*):(\d+)\s')

def _render_stack_with_links(self: Traceback, stack: Stack) -> Group:
    group = old_render_stack(self, stack)
    for r in group._renderables:
        if not isinstance(r, Text):
            continue
        m = FILENAME_LINE.match(str(r))
        if not m:
            continue
        fn, line = m.groups()
        p = Path(fn)
        if not p.exists():
            continue
        r.stylize("link %s#%s" % (p.as_uri(), line), 0, len(fn) + len(line) + 1)

    return group


def patch_traceback():
    global _is_patched

    if _is_patched:
        return True
    Traceback._render_stack = _render_stack_with_links  # type: ignore[method-assign]
    return True


def test_traceback():
    from actions.models import Action
    act = Action.objects.get(id='abcde')
    return act
