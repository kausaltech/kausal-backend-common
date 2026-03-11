from typing import TYPE_CHECKING, Any, Self

from pydantic import BaseModel


class StrawberryPydanticType[BaseM: BaseModel]:
    if TYPE_CHECKING:
        @classmethod
        def from_pydantic(cls, instance: BaseM, extra: dict[str, Any] | None = None) -> Self: ...  # pyright: ignore[reportUnusedParameter]

        def to_pydantic(self, **kwargs: Any) -> BaseM: ...  # pyright: ignore[reportUnusedParameter]
