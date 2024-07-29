from typing import Callable, overload, TypeVar


FN = TypeVar("FN", bound=Callable)



@overload
def register(hook_name: str) -> Callable[[FN], FN]: ...

@overload
def register(hook_name: str, fn: Callable, order: int = ...) -> None: ...


def get_hooks(hook_name: str) -> list[Callable]: ...
