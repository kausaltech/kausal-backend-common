from __future__ import annotations

from annotationlib import get_annotations
from typing import TYPE_CHECKING, Any, TypedDict, Unpack, cast, overload

import strawberry_django
from django.db import transaction
from django.db.models import Model
from django.utils import translation
from strawberry.extensions import FieldExtension
from strawberry.types.base import StrawberryOptional
from strawberry.types.fields.resolver import StrawberryResolver
from strawberry_django.fields.types import OperationInfo
from strawberry_django.mutations.fields import resolvers

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence

    from django.db.models import ForeignObjectRel, ManyToManyField
    from strawberry import Info
    from strawberry.extensions.field_extension import SyncExtensionResolver
    from strawberry.permission import BasePermission
    from strawberry.types.field import StrawberryField
    from strawberry_django.mutations.fields import DjangoMutationBase


class MutationExtension(FieldExtension):
    def __init__(self):
        super().__init__()

    def apply(self, field: StrawberryField) -> None:  # pragma: no cover
        pass

    def resolve(self, next_: SyncExtensionResolver, source: Any, info: Info, **kwargs: Any) -> Any:
        # Ensure that every mutation is atomic and that the language is always
        # set to English (for error messages).
        with translation.override('en'), transaction.atomic():
            ret = next_(source, info, **kwargs)
            if isinstance(ret, OperationInfo):
                for msg in ret.messages:
                    # Convert lazy strings to regular strings
                    msg.message = str(msg.message)
            return ret


class MutationArgs(TypedDict, total=False):
    name: str | None
    field_name: str | None
    is_subscription: bool
    description: str | None
    permission_classes: list[type[BasePermission]] | None
    deprecation_reason: str | None
    default: Any
    default_factory: Callable[..., object] | object
    metadata: Mapping[Any, Any] | None
    directives: Sequence[object] | None
    graphql_type: Any | None


OP_INFO_FRAGMENT = """
fragment OpInfo on OperationInfo {
    messages {
        kind
        message
        field
        code
    }
}
"""

type ResolverFunc = StrawberryResolver[Any] | Callable[..., Any] | staticmethod[Any, Any] | classmethod[Any, Any, Any]


type MutationField = DjangoMutationBase


@overload
def mutation[T: ResolverFunc](
    *, extensions: list[FieldExtension] | None = None, **kwargs: Unpack[MutationArgs]
) -> Callable[[T], MutationField]: ...


@overload
def mutation[T: ResolverFunc](
    resolver: T,  # pyright: ignore[reportInvalidTypeVarUse]
    *,
    extensions: list[FieldExtension] | None = None,
    **kwargs: Unpack[MutationArgs],
) -> MutationField: ...


def mutation[T: ResolverFunc](
    resolver: T | None = None,
    *,
    extensions: list[FieldExtension] | None = None,
    **kwargs: Unpack[MutationArgs],
) -> DjangoMutationBase | Callable[[T], MutationField]:
    extensions = list(extensions or ())
    for ext in extensions:
        if isinstance(ext, MutationExtension):
            break
    else:
        extensions.append(MutationExtension())
    field = strawberry_django.mutation(handle_django_errors=True, extensions=extensions, **kwargs)

    def wrap(resolver: T) -> MutationField:
        # if gql_type is None and resolver is not None:
        fixed_type = kwargs.get('graphql_type')
        annotations = get_annotations(resolver)
        if fixed_type is None and annotations.get('return') is None:
            field.type = StrawberryOptional(OperationInfo)
        return field(resolver)

    if resolver is not None:
        return wrap(resolver)
    return wrap


def parse_input(info: Info, data: Any) -> dict[str, Any]:
    return resolvers.parse_input(info, data)


def prepare_instance[M: Model](
    info: Info, model_or_instance: type[M] | M, cleaned_data: dict[str, Any]
) -> tuple[M, dict[str, object], list[tuple[ManyToManyField[Any, Any] | ForeignObjectRel, Any]]]:
    if isinstance(model_or_instance, Model):
        instance = model_or_instance
    else:
        instance = model_or_instance()
    prepared_instance, kwargs, m2m = resolvers.prepare_create_update(info=info, instance=instance, data=cleaned_data)
    return cast('M', prepared_instance), kwargs, m2m


def prepare_create_update[M: Model](
    info: Info, model_or_instance: type[M] | M, data: Any
) -> tuple[
    M,
    dict[str, object],
    list[tuple[ManyToManyField[Any, Any] | ForeignObjectRel, Any]],
]:
    parsed_data = parse_input(info, data)
    return prepare_instance(info, model_or_instance, parsed_data)
