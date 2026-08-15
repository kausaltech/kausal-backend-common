import inspect
from annotationlib import get_annotations
from types import UnionType
from typing import (
    TYPE_CHECKING,
    Any,
    Self,
    TypeAliasType,
    TypedDict,
    Union,  # pyright: ignore[reportDeprecated]
    Unpack,
    cast,
    dataclass_transform,
    get_args,
    get_origin,
)

import strawberry as sb
from pydantic import BaseModel
from strawberry import auto
from strawberry.experimental.pydantic import type as sb_pydantic_type
from strawberry.types.auto import StrawberryAuto
from strawberry.types.base import get_object_definition
from strawberry.types.field import StrawberryField

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from strawberry.annotation import StrawberryAnnotation


class StrawberryPydanticType[BaseM: BaseModel]:
    if TYPE_CHECKING:

        @classmethod
        def from_pydantic(cls, instance: BaseM, extra: dict[str, Any] | None = None) -> Self: ...  # pyright: ignore[reportUnusedParameter]

        def to_pydantic(self, **kwargs: Any) -> BaseM: ...  # pyright: ignore[reportUnusedParameter]

        _original_model: BaseM


type ValidConversionType = type | TypeAliasType

# Keyed by annotation objects: classes, PEP 695 type aliases, or typing
# special forms such as ``Literal[...]`` (which have no expressible static
# type of their own).
type_conversion_registry: dict[Any, type] = {}


def register_type_conversion(from_type: Any, to_type: type) -> None:
    type_conversion_registry[from_type] = to_type


def get_type_conversion(from_type: Any) -> type | None:
    return type_conversion_registry.get(from_type)


def _convert_type_annotation(type_ann: StrawberryAnnotation) -> None:
    ann = type_ann.annotation
    target = get_type_conversion(ann)
    if target is not None:
        type_ann.annotation = target
        return

    if isinstance(ann, UnionType):
        args = list(get_args(ann))
        args_out = []
        for arg in args:
            target = get_type_conversion(arg)
            if target is not None:
                args_out.append(target)
            else:
                args_out.append(arg)
        if args_out != args:
            type_ann.annotation = Union[tuple(args_out)]  # noqa: UP007  # pyright: ignore[reportDeprecated]


def _replace_i18n_fields(sb_type: type) -> None:
    sb_def = get_object_definition(sb_type, strict=True)
    for field in sb_def.fields:
        type_ann = field.type_annotation
        if not type_ann:
            continue
        _convert_type_annotation(type_ann)


class PydanticTypeKwargs(TypedDict, total=False):
    name: str | None
    is_input: bool
    is_interface: bool
    description: str | None
    directives: Sequence[object] | None
    all_fields: bool
    include_computed: bool
    use_pydantic_alias: bool


def _restore_classmethods(source: type, target: type) -> None:
    """
    Restore classmethods from source to target.

    strawberry.pydantic loses them on the way.
    """

    members = inspect.getmembers(source, inspect.ismethod)
    if not members:
        return
    for method_name, method in members:
        if hasattr(target, method_name):
            continue
        setattr(target, method_name, classmethod(method.__func__))


@dataclass_transform(
    order_default=True,
    kw_only_default=True,
    field_specifiers=(sb.field, StrawberryField),
)
def pydantic_type[T: type](
    model: type[BaseModel],
    **kwargs: Unpack[PydanticTypeKwargs],
) -> Callable[[T], T]:
    pydantic_wrap = sb_pydantic_type(model, **kwargs)

    def wrapper(cls: T) -> T:
        from strawberry.types.maybe import Maybe

        annotations = get_annotations(cls)
        maybe_fields = {}
        for key, value in annotations.items():
            if isinstance(value, str):
                msg = (
                    f'{cls.__module__}.{cls.__name__} annotation for `{key}` is a string, not a type. '
                    + 'Remove the future annotations import.'
                )
                raise TypeError(msg)
            if get_origin(value) is Maybe:
                args = get_args(value)
                for arg in args:
                    if not isinstance(arg, StrawberryAuto):
                        continue
                    maybe_fields[key] = value
                    cls.__annotations__[key] = auto
                    break

        sb_type = cast('T', pydantic_wrap(cls))

        _replace_i18n_fields(sb_type)
        sb_def = get_object_definition(sb_type, strict=True)
        for field in sb_def.fields:
            if field.name not in maybe_fields:
                continue
            type_ann = field.type_annotation
            assert type_ann is not None
            type_ann.annotation = Maybe[type_ann.annotation]  # type: ignore[misc, name-defined]

        _restore_classmethods(cls, sb_type)

        return sb_type

    return wrapper


def pydantic_input[T: type](model: type[BaseModel], **kwargs: Unpack[PydanticTypeKwargs]) -> Callable[[T], T]:
    kwargs['is_input'] = True
    return pydantic_type(model, **kwargs)


def graphql_types[M: BaseModel](model_cls: type[M]) -> type[M]:
    """
    Build the GraphQL projections declared as classes nested in a Pydantic model.

    A nested ``ObjectType`` stub becomes the strawberry object type for the
    model (named after the model) and a nested ``InputType`` stub the input
    type (named ``<Model>Input``); both are rebuilt in place, so callers
    reference ``Model.ObjectType`` / ``Model.InputType``. The stubs live in
    the model body, where the model name is not yet bound — this outer
    decorator supplies the model to ``pydantic_type`` once it exists.
    """

    def build(stub: type, name: str, builder: Callable[..., Callable[[type], type]]) -> type:
        built = builder(model_cls, name=name)(stub)
        built.__name__ = name
        built.__qualname__ = f'{model_cls.__qualname__}.{name}'
        return built

    object_stub = model_cls.__dict__.get('ObjectType')
    if object_stub is not None:
        model_cls.ObjectType = build(object_stub, model_cls.__name__, pydantic_type)  # type: ignore[attr-defined]
    input_stub = model_cls.__dict__.get('InputType')
    if input_stub is not None:
        model_cls.InputType = build(input_stub, f'{model_cls.__name__}Input', pydantic_input)  # type: ignore[attr-defined]
    if object_stub is None and input_stub is None:
        msg = f'{model_cls.__module__}.{model_cls.__name__} declares no nested ObjectType or InputType stub'
        raise TypeError(msg)
    return model_cls
