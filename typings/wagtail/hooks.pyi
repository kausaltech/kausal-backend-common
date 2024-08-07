from typing import Callable, TypeVar, overload

_FN = TypeVar("_FN", bound=Callable)

@overload
def register(hook_name: str) -> Callable[[_FN], _FN]: ...

@overload
def register(hook_name: str, fn: Callable, order: int = ...) -> None: ...


def get_hooks(hook_name: str) -> list[Callable]: ...
