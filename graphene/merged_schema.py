from __future__ import annotations

import inspect
from typing import TYPE_CHECKING, cast

import graphene
from graphene.types.schema import TypeMap as GrapheneTypeMap
from graphql import (
    GraphQLField,
    GraphQLNamedType,
    GraphQLNullableType,
    GraphQLObjectType,
    assert_named_type,
)
from strawberry.annotation import StrawberryAnnotation
from strawberry.federation.schema import Schema as FederationSchema
from strawberry.schema.schema_converter import GraphQLCoreConverter
from strawberry.schema.types import ConcreteType
from strawberry.schema.types.scalar import DEFAULT_SCALAR_REGISTRY
from strawberry.types import has_object_definition
from strawberry.types.base import StrawberryObjectDefinition, StrawberryType
from strawberry.types.enum import EnumDefinition
from strawberry.types.scalar import ScalarDefinition
from strawberry.types.union import StrawberryUnion

type StrawberryObjectType = StrawberryObjectDefinition | EnumDefinition | ScalarDefinition


def get_sb_definition(type_: type) -> StrawberryObjectType | StrawberryUnion:
    from strawberry.types.base import StrawberryObjectDefinition
    from strawberry.types.enum import EnumDefinition
    from strawberry.types.scalar import ScalarDefinition

    if TYPE_CHECKING:
        from graphene.types.enum import EnumOptions
        from graphene.types.inputobjecttype import InputObjectTypeOptions
        from graphene.types.interface import InterfaceOptions
        from graphene.types.objecttype import ObjectTypeOptions
        from graphene.types.scalars import ScalarOptions
        from graphene.types.union import UnionOptions

    type_meta = getattr(type_, '_meta', None)
    meta: ObjectTypeOptions | InterfaceOptions | EnumOptions | ScalarOptions | InputObjectTypeOptions | UnionOptions
    if issubclass(type_, graphene.ObjectType):
        meta = cast('ObjectTypeOptions', type_meta)
        return StrawberryObjectDefinition(
            name=meta.name,
            is_input=False,
            is_interface=False,
            origin=type_,
            description=meta.description,
            interfaces=[],
            extend=False,
            directives=(),
            is_type_of=None,
            resolve_type=None,
            fields=[],
        )
    if issubclass(type_, graphene.InputObjectType):
        meta = cast('InputObjectTypeOptions', type_meta)
        return StrawberryObjectDefinition(
            name=meta.name,
            is_input=True,
            is_interface=False,
            origin=type_,
            description=meta.description,
            interfaces=[],
            extend=False,
            directives=(),
            is_type_of=None,
            resolve_type=None,
            fields=[],
        )
    if issubclass(type_, graphene.Interface):
        meta = cast('InterfaceOptions', type_meta)
        return StrawberryObjectDefinition(
            name=meta.name,
            is_input=False,
            is_interface=False,
            origin=type_,
            description=meta.description,
            interfaces=[],
            extend=False,
            directives=(),
            is_type_of=None,
            resolve_type=None,
            fields=[],
        )
    if issubclass(type_, graphene.Union):
        meta = cast('UnionOptions', type_meta)
        ret = StrawberryUnion(
            name=meta.name,
            type_annotations=tuple(StrawberryAnnotation(type_) for type_ in meta.types),
            description=meta.description,
        )
        return ret

    if issubclass(type_, graphene.Enum):
        meta = cast('EnumOptions', type_meta)
        return EnumDefinition(
            wrapped_cls=type(meta.enum),  # type: ignore
            name=meta.name,
            values=[],
            description=meta.description,
        )
    if issubclass(type_, graphene.Scalar):
        meta = cast('ScalarOptions', type_meta)
        return ScalarDefinition(
            name=meta.name,
            description=meta.description,
            specified_by_url=None,
            serialize=None,
            parse_value=None,
            parse_literal=None,
        )

    raise TypeError("Unknown type %s" % type_)


SB_SCALAR_TYPES = {val.name: key for key, val in DEFAULT_SCALAR_REGISTRY.items()}

class UnifiedGrapheneTypeMap(GrapheneTypeMap):
    def __init__(self, sb_converter: UnifiedGraphQLConverter):
        self.sb_converter = sb_converter
        super().__init__(types=())

    def add_type(self, type_: type[graphene.ObjectType] | type) -> GraphQLNamedType:
        from graphene.types.base import SubclassWithMeta

        if isinstance(type_, (graphene.NonNull, graphene.List)):
            return super().add_type(type_)

        if has_object_definition(type_):
            gql_type = assert_named_type(self.sb_converter.from_type(type_))
            self[gql_type.name] = gql_type
            return gql_type

        assert issubclass(type_, SubclassWithMeta)
        name: str = getattr(type_, '_meta').name  # noqa: B009
        sb_type = self.sb_converter.type_map.get(name)
        if sb_type is not None:
            return assert_named_type(sb_type.implementation)

        sb_scalar_type = SB_SCALAR_TYPES.get(name)
        if sb_scalar_type is not None:
            return self.sb_converter.from_scalar(cast('type', sb_scalar_type))

        gql_type = cast('GraphQLNamedType', super().add_type(type_))
        if gql_type.name not in self.sb_converter.type_map:
            sb_def = get_sb_definition(type_)
            self.sb_converter.type_map[gql_type.name] = ConcreteType(
                definition=sb_def, implementation=gql_type
            )

        return gql_type


class UnifiedGraphQLConverter(GraphQLCoreConverter):
    graphene_type_map: UnifiedGrapheneTypeMap

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.graphene_type_map = UnifiedGrapheneTypeMap(self)

    def add_graphene_type(self, type_: type) -> GraphQLNamedType:
        return self.graphene_type_map.add_type(type_)

    def from_type(self, type_: StrawberryType | type) -> GraphQLNullableType:
        if inspect.isclass(type_):  # noqa: SIM102
            if issubclass(type_, (graphene.ObjectType, graphene.Interface, graphene.Union)):
                return cast('GraphQLNullableType', self.add_graphene_type(type_))
        try:
            ret = super().from_type(type_)
        except Exception as e:
            raise e
        return ret

    def _merge_graphene_object_fields(self, gql_type: GraphQLObjectType, graphene_type: type[graphene.ObjectType]) -> None:
        fields: dict[str, GraphQLField] = self.graphene_type_map.create_fields_for_type(graphene_type)
        for name, field in fields.items():
            if name in gql_type.fields:
                raise ValueError(f"Field {name} already exists in {gql_type}")
            gql_type.fields[name] = field

    def get_graphql_fields(
        self, type_definition: StrawberryObjectDefinition
    ) -> dict[str, GraphQLField]:
        fields = super().get_graphql_fields(type_definition)
        origin = type_definition.origin
        if issubclass(origin, graphene.ObjectType):
            # Merge fields from object types that are _both_ Strawberry and Graphene (mostly Query?).
            graphene_fields: dict[str, GraphQLField] = self.graphene_type_map.create_fields_for_type(origin)
            for name, field in graphene_fields.items():
                if name in fields:
                    raise ValueError(f"Field {name} already exists in {type_definition.name}")
                fields[name] = field
        return fields


class GrapheneStrawberrySchema(FederationSchema):
    _schema_converter: GraphQLCoreConverter

    # Since Strawberry doesn't support a custom GraphQLCoreConverter yet, we need to
    # resort to a hack to use our own subclass.
    @property
    def schema_converter(self) -> GraphQLCoreConverter:
        return self._schema_converter

    @schema_converter.setter
    def schema_converter(self, value: GraphQLCoreConverter) -> None:
        opt_kwargs = {}
        if not hasattr(value, '_get_scalar_registry'):
            opt_kwargs['scalar_registry'] = value.scalar_registry
        else:
            opt_kwargs['scalar_overrides'] = {}
        # scalar_overrides is missing
        self._schema_converter = UnifiedGraphQLConverter(
            config=value.config,
            get_fields=value.get_fields,
            **opt_kwargs,
        )
