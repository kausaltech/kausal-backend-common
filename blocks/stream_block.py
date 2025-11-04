from __future__ import annotations

from typing import TYPE_CHECKING, Any

from wagtail import blocks

from grapple.helpers import register_streamfield_block

if TYPE_CHECKING:
    from collections.abc import Iterable

    from django.db.models import Model

    from kausal_common.blocks.registry import FieldBlockContext, ModelFieldRegistry


def generate_stream_block[M: Model](
    name: str,
    fields: Iterable[str | tuple[str, blocks.Block[Any]]],
    block_context: FieldBlockContext,
    field_registry: ModelFieldRegistry[M],
    mixins: tuple[type, ...] | None = None,
    extra_classvars: dict[str, Any] | None = None,
) -> type[blocks.StreamBlock]:
    """
    Dynamically generates a stream block based on desired action fields.

    If an element in the fields iterable is a tuple, the first of the pair is the field name
    and the last of the pair is an already instantiated block that can be directly used.

    If an element is a string, the action field registry will be used to
    retrieve the correct block for that action field. (Those might be dynamically
    created classes or customized static classes.)

    If support_editing_from_other_form is True, add support to edit
    part of this block from a related model instance's edit form.
    Currently we support editing
      - an AttributeType's block from within the AttributeType's edit form and
      - a CategoryType's block from within the CategoryType's edit form.
    """
    if mixins is None:
        mixins = tuple()

    if extra_classvars is None:
        extra_classvars = dict()

    field_blocks = {}
    graphql_types = list()
    for field in fields:
        target_field_name = None
        field_block = None
        if isinstance(field, tuple):
            field_name, field_block = field
            target_field_name = field_name
        else:
            field_name = field
            target_field_name = field_name
        if not field_block:
            field_block = field_registry.get_block(block_context, field_name)

        field_block_class = type(field_block)
        if field_block_class not in graphql_types:
            graphql_types.append(field_block_class)
        # if field_block_class not in grapple_registry.streamfield_blocks:
        #     register_streamfield_block(field_block_class)
        field_blocks[target_field_name] = field_block

    block_class = type(name, (*mixins, blocks.StreamBlock), {
        '__module__': __name__,
        **field_blocks,
        **extra_classvars,
        'graphql_types': graphql_types,
    })

    register_streamfield_block(block_class)
    return block_class
