import dataclasses
from typing import (
    TYPE_CHECKING,
    Any,
    overload,
)

from strawberry.annotation import StrawberryAnnotation
from strawberry.types.field import StrawberryField

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence
    from typing import Literal

    from strawberry.extensions.field_extension import FieldExtension
    from strawberry.permission import BasePermission
    from strawberry.types.field import _RESOLVER_TYPE, _RESOLVER_TYPE_SYNC


@overload
def field(
    *,
    name: str | None = None,
    is_subscription: bool = False,
    description: str | None = None,
    init: Literal[True] = True,
    permission_classes: list[type[BasePermission]] | None = None,
    deprecation_reason: str | None = None,
    default: Any = dataclasses.MISSING,
    default_factory: Callable[..., object] | object = dataclasses.MISSING,
    metadata: Mapping[Any, Any] | None = None,
    directives: Sequence[object] | None = (),
    extensions: list[FieldExtension] | None = None,
    graphql_type: Any | None = None,
) -> Any: ...


@overload
def field[T, FieldT: StrawberryField = StrawberryField](
    resolver: _RESOLVER_TYPE_SYNC[T],
    *,
    name: str | None = None,
    is_subscription: bool = False,
    description: str | None = None,
    permission_classes: list[type[BasePermission]] | None = None,
    deprecation_reason: str | None = None,
    default: Any = dataclasses.MISSING,
    default_factory: Callable[..., object] | object = dataclasses.MISSING,
    metadata: Mapping[Any, Any] | None = None,
    directives: Sequence[object] | None = (),
    extensions: list[FieldExtension] | None = None,
    graphql_type: Any | None = None,
    custom_field_class: type[FieldT] | None = None,
) -> FieldT: ...


def field(  # noqa: PLR0913
    resolver: _RESOLVER_TYPE[Any] | None = None,
    *,
    name: str | None = None,
    is_subscription: bool = False,
    description: str | None = None,
    permission_classes: list[type[BasePermission]] | None = None,
    deprecation_reason: str | None = None,
    default: Any = dataclasses.MISSING,
    default_factory: Callable[..., object] | object = dataclasses.MISSING,
    metadata: Mapping[Any, Any] | None = None,
    directives: Sequence[object] | None = (),
    extensions: list[FieldExtension] | None = None,
    graphql_type: Any | None = None,
    custom_field_class: type[StrawberryField] | None = None,
    # This init parameter is used by PyRight to determine whether this field
    # is added in the constructor or not. It is not used to change
    # any behavior at the moment.
    init: Literal[True, False] | None = None,
) -> Any:
    type_annotation = StrawberryAnnotation.from_annotation(graphql_type)

    field_class = custom_field_class or StrawberryField

    field_ = field_class(
        python_name=None,
        graphql_name=name,
        type_annotation=type_annotation,
        description=description,
        is_subscription=is_subscription,
        permission_classes=permission_classes or [],
        deprecation_reason=deprecation_reason,
        default=default,
        default_factory=default_factory,
        metadata=metadata,
        directives=directives or (),
        extensions=extensions or [],
    )

    if resolver:
        assert init is not True, "Can't set init as True when passing a resolver."
        return field_(resolver)
    return field_
