# ruff: noqa: ANN401
from typing import Any, Self, Sequence, overload

from django.db.models.fields import SlugField

class AutoSlugField(SlugField):
    @classmethod
    def __new__(
        cls, *args: Any, always_update: bool = ..., populate_from: str | None = ...,
        unique_with: str | Sequence[str] = ..., **kwargs: Any,
    ) -> Self: ...

    @overload
    def __init__(
        self, *args: Any, always_update: bool = ..., populate_from: str | None = ...,
        unique_with: str | Sequence[str] = ..., **kwargs: Any,
    ): ...

    @overload
    def __init__(self, *args, **kwargs) -> None: ...
