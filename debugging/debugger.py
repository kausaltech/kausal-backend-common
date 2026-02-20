from __future__ import annotations

from pdb import Pdb
from typing import TYPE_CHECKING, Any

from rich import print
from rich.pretty import Pretty
from rich.style import Style

if TYPE_CHECKING:

    from IPython.core.debugger import Pdb as IPythonPdb
    class PdbMixinBase(IPythonPdb): ...
else:
    class PdbMixinBase: ...


class PdbMixin(PdbMixinBase):

    def print_stack_trace(self, count: int | None = None):
        if count is None:
            count = self.context
        Pdb.print_stack_trace(self)

    if False:
        def __line_content(self, filename: str, lineno: int, line: str, arrow: bool = False):  # noqa: ANN202
            bp, num, colored_line = super().__line_content(filename, lineno, line, arrow)
            print(colored_line)
            link_style = Style(link=f'file://{filename}#{lineno}')
            num = link_style.render(num)
            return bp, num, colored_line

        def displayhook(self, obj: Any):
            if obj is not None:
                print(Pretty(obj))

        def do_p(self, arg: str) -> None:
            if not arg:
                self._print_invalid_arg(arg)  # type: ignore[attr-defined]
                return
            try:
                val = self._getval(arg)
            except:  # noqa: E722
                return  # _getval() has displayed the error
            print(val)
            return


def get_debugger_cls() -> type[Pdb]:
    from ipdb.__main__ import _get_debugger_cls  # pyright: ignore[reportMissingTypeStubs]
    from pdbr.utils import debugger_cls  # pyright: ignore[reportMissingTypeStubs]
    base_class = _get_debugger_cls()
    pdbr_class = debugger_cls(base_class, show_layouts=False)
    return type('Pdb', (PdbMixin, pdbr_class), {})


if __name__ == '__main__':
    kls = get_debugger_cls()
    pdb = kls()
    pdb.set_trace()
