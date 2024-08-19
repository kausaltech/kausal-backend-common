from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field


@dataclass
class SingleValueContext[ValueT]:
    context_name: str
    container_type: type[ValueT]

    _context_var: ContextVar[ValueT] = field(init=False)

    def __post_init__(self):
        self._context_var = ContextVar(self.context_name)

    @contextmanager
    def activate(self, value: ValueT):
        """
        Set this context as the currently active one.

        When the runtime context finishes, the previous context (if any) will be restored.
        """
        token = self._context_var.set(value)
        try:
            yield
        finally:
            self._context_var.reset(token)

    def get(self) -> ValueT:
        return self._context_var.get()


@dataclass
class SubclassableContext(SingleValueContext):
    def get_as_type[SubClassT](self, klass: type[SubClassT]) -> SubClassT:
        val = self.get()
        if not isinstance(val, klass):
            raise TypeError("Context value type is '%s'; expected '%s'" % (type(val), klass))
        return val
