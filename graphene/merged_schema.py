from __future__ import annotations

import inspect
from typing import TYPE_CHECKING, Any, Generic, TypeGuard, cast

import graphene
from graphene.types.schema import TypeMap as GrapheneTypeMap
from graphql import (
    GraphQLField,
    GraphQLNamedType,
    GraphQLNullableType,
    GraphQLObjectType,
    assert_enum_type,
    assert_named_type,
)
from strawberry.annotation import StrawberryAnnotation
from strawberry.federation.schema import Schema as FederationSchema
from strawberry.schema.schema_converter import GraphQLCoreConverter
from strawberry.schema.types import ConcreteType
from strawberry.schema.types.scalar import DEFAULT_SCALAR_REGISTRY
from strawberry.types import has_object_definition
from strawberry.types.base import (
    StrawberryObjectDefinition,
    StrawberryType,
    WithStrawberryDefinition,
    has_strawberry_definition,
)
from strawberry.types.enum import StrawberryEnumDefinition, WithStrawberryEnumDefinition, has_enum_definition
from strawberry.types.scalar import ScalarDefinition
from strawberry.types.union import StrawberryUnion

type StrawberryObjectType = StrawberryObjectDefinition | StrawberryEnumDefinition | ScalarDefinition


def get_sb_definition(type_: type) -> StrawberryObjectType | StrawberryUnion:
    from strawberry.types.base import StrawberryObjectDefinition
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
        enum_def = StrawberryEnumDefinition(
            wrapped_cls=type(meta.enum),  # type: ignore  # pyright: ignore[reportArgumentType]
            name=meta.name,
            values=[],
            description=meta.description,
        )
        return enum_def

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


def _get_graphene_type_name(type_: type) -> str | None:
    meta = getattr(type_, '_meta', None)
    if meta is None:
        return None
    name = getattr(meta, 'name', None)
    if name is None:
        return None
    return name


def _is_graphene_named_type(
    type_: Any,
) -> TypeGuard[type[graphene.ObjectType[Any] | graphene.Interface[Any] | graphene.Union | graphene.Enum]]:
    if not inspect.isclass(type_):
        return False
    if not issubclass(type_, (graphene.ObjectType, graphene.InputObjectType, graphene.Interface, graphene.Union, graphene.Enum)):
        return False
    return True


def _is_strawberry_type(type_: Any) -> TypeGuard[WithStrawberryDefinition[Any]]:
    return has_strawberry_definition(type_)

def is_strawberry_enum(type_: Any) -> TypeGuard[WithStrawberryEnumDefinition]:
    return has_enum_definition(type_)

def _get_strawberry_enum_def(type_: Any) -> StrawberryEnumDefinition | None:
    if has_enum_definition(type_):
        return type_.__strawberry_definition__
    return None


SB_SCALAR_TYPES = {val.name: key for key, val in DEFAULT_SCALAR_REGISTRY.items()}

class UnifiedGrapheneTypeMap(GrapheneTypeMap):
    """Graphene TypeMap that can handle both Strawberry and Graphene types."""

    def __init__(self, sb_converter: UnifiedGraphQLConverter) -> None:
        self.sb_converter = sb_converter
        super().__init__(types=())

    def _add_strawberry_type(self, type_: type, gql_type: GraphQLNamedType, name: str) -> None:
        sb_def: StrawberryObjectType | StrawberryUnion
        if enum_def := _get_strawberry_enum_def(type_):
            sb_def = enum_def
        else:
            sb_def = get_sb_definition(type_)
        self.sb_converter.type_map[name] = ConcreteType(
            definition=sb_def, implementation=gql_type
        )
        if not _is_strawberry_type(type_): # and enum_def is not None:
            # We need to set the Strawberry definition so that Strawberry input type conversion works.
            setattr(type_, '__strawberry_definition__', sb_def)  # noqa: B010
            if issubclass(type_, Generic):
                assert not hasattr(type_, '__parameters__')
                setattr(type_, '__parameters__', ())  # noqa: B010
            setattr(type_, '__graphene_primary__', True)  # noqa: B010

    def add_type(self, type_: type[graphene.ObjectType[Any]] | type) -> GraphQLNamedType:
        from graphene.types.base import SubclassWithMeta

        if isinstance(type_, (graphene.NonNull, graphene.List)):
            return super().add_type(type_)

        graphene_type_name = _get_graphene_type_name(type_)
        if graphene_type_name in self:
            return self[graphene_type_name]

        if has_object_definition(type_) and not _is_graphene_named_type(type_):
            gql_type = assert_named_type(self.sb_converter.from_type(type_))
            self[gql_type.name] = gql_type
            return gql_type

        if is_strawberry_enum(type_) and not _is_graphene_named_type(type_):
            enum_definition: StrawberryEnumDefinition = type_.__strawberry_definition__
            assert enum_definition.name
            assert enum_definition.name not in self, "Enum %s already exists" % enum_definition.name
            enum_type = assert_enum_type(self.sb_converter.from_type(enum_definition))
            self[enum_type.name] = enum_type
            return enum_type

        if not issubclass(type_, SubclassWithMeta):
            raise TypeError(f"Type {type_} is not a subclass of SubclassWithMeta")

        name: str = getattr(type_, '_meta').name  # noqa: B009

        sb_type = self.sb_converter.type_map.get(name)
        if sb_type is not None and not getattr(type_, '__graphene_primary__', False):
            return assert_named_type(sb_type.implementation)

        sb_scalar_type = SB_SCALAR_TYPES.get(name)
        if sb_scalar_type is not None:
            return self.sb_converter.from_scalar(cast('type', sb_scalar_type))

        gql_type = super().add_type(type_)

        assert gql_type.name == name
        if name not in self.sb_converter.type_map:
            self._add_strawberry_type(type_, gql_type, name)

        return gql_type


class UnifiedGraphQLConverter(GraphQLCoreConverter):
    """Strawberry GraphQLCoreConverter that can handle both Strawberry and Graphene types."""

    graphene_type_map: UnifiedGrapheneTypeMap

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.graphene_type_map = UnifiedGrapheneTypeMap(self)

    def add_graphene_type(self, type_: type) -> GraphQLNamedType:
        graphene_type_name = _get_graphene_type_name(type_)
        if graphene_type_name is not None and graphene_type_name in self.graphene_type_map:
            return self.graphene_type_map[graphene_type_name]
        return self.graphene_type_map.add_type(type_)

    def from_type(self, type_: StrawberryType | type) -> GraphQLNullableType:
        if _is_graphene_named_type(type_):
            return cast('GraphQLNullableType', self.add_graphene_type(type_))
        try:
            ret = super().from_type(type_)
        except Exception:  # noqa: TRY203
            raise
        return ret

    def _merge_graphene_object_fields(self, gql_type: GraphQLObjectType, graphene_type: type[graphene.ObjectType[Any]]) -> None:
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
        self._schema_converter = UnifiedGraphQLConverter(
            config=value.config,
            scalar_overrides={},
            scalar_map={},
            get_fields=value.get_fields,
        )
        self._schema_converter.scalar_registry = value.scalar_registry
