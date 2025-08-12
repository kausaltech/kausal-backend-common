from __future__ import annotations

from typing import TYPE_CHECKING

import graphene
from django.db import models
from wagtail.blocks.stream_block import StreamBlock, StreamValue
from wagtail.blocks.struct_block import StructBlock
from wagtail.fields import StreamField

from grapple.models import GraphQLField
from grapple.registry import registry

if TYPE_CHECKING:
    from collections.abc import Callable

    from wagtail import blocks


def make_grapple_field(
    field_name: str, block_type: type[blocks.StructBlock], is_list: bool = False, required: bool = True
) -> Callable[[], GraphQLField]:
    def resolve() -> GraphQLField:
        ret = registry.streamfield_blocks[block_type]
        if required:
            ret = graphene.NonNull(ret)
        if is_list:
            ret = graphene.List(ret)
        return GraphQLField(field_name, ret)

    return resolve


def make_grapple_streamfield(get_class: Callable[[], type], field_name: str) -> Callable[[], GraphQLField]:
    def resolve() -> GraphQLField:
        cls = get_class()
        type_name = cls.__name__
        union_name = f'{type_name}{field_name.capitalize()}Union'
        if issubclass(cls, models.Model):
            field = cls._meta.get_field(field_name)
            assert isinstance(field, StreamField)
            stream_block = field.stream_block
            required = not field.null
        elif issubclass(cls, StructBlock):
            field_block = cls.base_blocks[field_name]
            assert isinstance(field_block, StreamBlock)
            stream_block = field_block
            required = not field_block.required
        else:
            raise TypeError(f'{cls} is not a model or a streamfield block')

        child_blocks = stream_block.child_blocks.values()
        for block in child_blocks:
            if type(block) not in registry.streamfield_blocks:
                raise TypeError(f'{type(block)} is not registered to grapple registry as streamfield block')
        child_types = [registry.streamfield_blocks[type(x)] for x in child_blocks]

        if len(child_types) == 1:
            return GraphQLField(field_name, graphene.List(graphene.NonNull(child_types[0])), required=required)

        class Meta:
            types = tuple(child_types)

        def resolve_type(instance: StreamValue.StreamChild, info) -> type[graphene.ObjectType]:
            return registry.streamfield_blocks[type(instance.block)]

        union_class = type(union_name, (graphene.Union,), {'Meta': Meta, 'resolve_type': resolve_type})

        return GraphQLField(field_name, graphene.List(graphene.NonNull(union_class)), required=required)

    return resolve
