from __future__ import annotations

import inspect
from typing import TYPE_CHECKING, Any, get_args, get_origin

import strawberry
from strawberry.extensions import FieldExtension

from kausal_common.models.types import copy_signature
from kausal_common.strawberry.fields import field

if TYPE_CHECKING:
    from strawberry import Info
    from strawberry.extensions.field_extension import SyncExtensionResolver
    from strawberry.types.field import StrawberryField


def resolve_grapple_type(type_: type) -> type | None:
    from wagtail.models import Page
    from wagtail.rich_text import RichText as WagtailRichText

    from grapple.registry import registry
    from grapple.types.rich_text import RichText as RichTextType

    if not inspect.isclass(type_):
        return None
    if issubclass(type_, Page):
        if type_ in registry.pages:
            return registry.pages[type_]
    elif type_ in registry.streamfield_blocks:
        return registry.streamfield_blocks[type_]
    elif type_ is WagtailRichText:
        return RichTextType
    return None


class GrappleRegistryType(FieldExtension):
    """Resolves types in the Grapple registry."""

    def resolve(self, next_: SyncExtensionResolver, source: Any, info: Info, **kwargs: Any) -> Any:
        return next_(source, info, **kwargs)

    def apply(self, field: StrawberryField) -> None:
        annotation = field.type_annotation
        if annotation is None:
            return
        evaled = annotation.evaluate()
        origin = get_origin(evaled)
        if origin is None:
            types = [evaled]
        else:
            types = list(get_args(evaled))

        new_types = []

        for type_ in types:
            new_type = resolve_grapple_type(type_) or type_
            new_types.append(new_type)

        if new_types != types:
            annotation.annotation = origin[*new_types] if origin else new_types[0]


@copy_signature(strawberry.field)
def grapple_field(*args, custom_field_class: type[StrawberryField] | None = None, **kwargs):
    extensions = list(kwargs.pop('extensions', []))
    extensions.append(GrappleRegistryType())

    return field(*args, extensions=extensions, custom_field_class=custom_field_class, **kwargs)
