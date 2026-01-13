from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

import graphene
from django.db import models
from graphene.types.base import BaseType
from graphene.types.field import Field
from wagtail.blocks.stream_block import StreamBlock, StreamValue
from wagtail.blocks.struct_block import StructBlock
from wagtail.fields import StreamField

from grapple.models import GraphQLField
from grapple.registry import registry

if TYPE_CHECKING:
    from collections.abc import Callable

    from graphene.types.field import Field
    from graphene.types.mountedtype import OrderedType
    from graphene.types.structures import Structure
    from wagtail import blocks

    from kausal_common.graphene import GQLInfo


def make_grapple_field(
    field_name: str, block_type: type[blocks.StructBlock], is_list: bool = False, required: bool = True,
) -> Callable[[], GraphQLField]:
    def resolve() -> GraphQLField:
        ret = registry.streamfield_blocks[block_type]
        if required:
            ret = graphene.NonNull(ret)
        if is_list:
            ret = graphene.List(ret)
        return GraphQLField(field_name, ret)

    return resolve

type GrappleWrapperField = tuple[GraphQLField, Callable[[Any], Any]]
type GrappleFieldDef = GraphQLField | GrappleWrapperField

def grapple_field[T: BaseType](
    field_name: str, field_type: type[T] | Callable[[], type[T]] | str, resolver: Callable[..., Any] | None = None,
    is_list: bool = False, required: bool = True,
) -> Callable[[], GrappleFieldDef]:
    def get_wrapper(field) -> graphene.Field:
        wrapped: Structure = field
        if is_list:
            wrapped = graphene.List(graphene.NonNull(wrapped))
        if required:
            wrapped = graphene.NonNull(wrapped)
        return graphene.Field(wrapped, resolver=resolver)

    def resolve() -> GrappleFieldDef:
        field = GraphQLField(field_name, field_type)
        if not is_list and not required and resolver is None:
            return field
        return field, get_wrapper
    return resolve


def _get_graphql_wrapper(field_name: str, is_list: bool, required: bool) -> Callable[[OrderedType], Field]:
    def get_wrapper(field: OrderedType) -> Field:
        wrapper: OrderedType

        if is_list:
            wrapper = graphene.List(graphene.NonNull(field))
        else:
            wrapper = field
        if required:
            wrapper = graphene.NonNull(wrapper)

        def resolve_streamfield(root, _info: GQLInfo) -> StreamValue | None:
            stream_value: StreamValue | None = getattr(root, field_name)
            if stream_value is None:
                return None
            # FIXME: Walk through all descendants?
            for block in stream_value:
                setattr(block, '_stream_container', root)  # noqa: B010
                setattr(block, '_stream_value', stream_value)  # noqa: B010
            return stream_value

        return graphene.Field(wrapper, resolver=resolve_streamfield)
    return get_wrapper


def _make_union_streamfield(
    cls: type, field_name: str, child_types: list[type], required: bool = True
) -> tuple[GraphQLField, Callable[[Any], Any]]:
    class Meta:
        types = tuple(child_types)

    def resolve_type(instance: StreamValue.StreamChild, _info: GQLInfo) -> type[graphene.ObjectType[Any]]:
        return registry.streamfield_blocks[type(instance.block)]

    type_name = cls.__name__
    field_name_camel = ''.join(word.capitalize() for word in field_name.split('_'))
    union_name = f'{type_name}{field_name_camel}Union'
    union_class = type(union_name, (graphene.Union,), {'Meta': Meta, 'resolve_type': resolve_type})

    return (
        GraphQLField(field_name, field_type=union_class), _get_graphql_wrapper(field_name, is_list=True, required=required)
    )


def make_grapple_streamfield(
    get_class: Callable[[], type], field_name: str
) -> Callable[[], GraphQLField | tuple[GraphQLField, Callable[[Any], Any]]]:
    def resolve() -> GraphQLField | tuple[GraphQLField, Callable[[Any], Any]]:
        cls = get_class()
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
        child_types = []
        for child_type in child_blocks:
            graphene_type = registry.streamfield_blocks[type(child_type)]
            if graphene_type in child_types:
                continue
            child_types.append(graphene_type)

        if len(child_types) == 1:
            return GraphQLField(field_name, graphene.List(graphene.NonNull(child_types[0])), required=required)

        return _make_union_streamfield(cls, field_name, child_types, required)

    return resolve
