from __future__ import annotations

from typing import TYPE_CHECKING, cast

import graphene
from graphene.types.schema import TypeMap as GrapheneTypeMap
from graphql import (
    GraphQLAbstractType,
    GraphQLDirective,
    GraphQLField,
    GraphQLNamedType,
    GraphQLObjectType,
    GraphQLScalarType,
    GraphQLSchema,
    GraphQLType,
    introspection_types,
    is_abstract_type,
)
from strawberry.types import has_object_definition

if TYPE_CHECKING:
    from collections.abc import Sequence

    import strawberry


class SchemaMerger:
    """Converts a GraphQL schema to a Strawberry schema."""

    def __init__(self, sb_schema: strawberry.Schema, gr_schema: graphene.Schema):
        self.sb_schema = cast(GraphQLSchema, sb_schema._schema)
        self.gr_schema = cast(GraphQLSchema, gr_schema.graphql_schema)

        sb_query_type = self.sb_schema.query_type
        assert sb_query_type is not None
        gr_query_type = self.gr_schema.query_type
        assert gr_query_type is not None

        ignore_types = set[str](key for key in introspection_types.keys())
        ignore_types.add(sb_query_type.name)
        ignore_types.add(gr_query_type.name)
        query_type = self.merge_object_types(sb_query_type, gr_query_type)
        directives = self.merge_directives(self.sb_schema.directives, self.gr_schema.directives)

        types = self.merge_types(
            tuple(self.sb_schema.type_map.values()),
            tuple(self.gr_schema.type_map.values()),
            ignore_types,
        )
        self.merged_schema = GraphQLSchema(
            query=query_type,
            directives=directives,
            extensions=self.sb_schema.extensions | self.gr_schema.extensions,
            types=types,
        )

    def merge_types(
        self, sb_types: Sequence[GraphQLNamedType], gr_types: Sequence[GraphQLNamedType], ignore_types: set[str]
    ) -> list[GraphQLNamedType]:
        def should_include(type_: GraphQLNamedType) -> bool:
            if type_.name in ignore_types:
                return False
            if isinstance(type_, GraphQLScalarType):
                return False
            return True

        types: list[GraphQLNamedType] = [type_ for type_ in sb_types if should_include(type_)]
        type_map: dict[str, GraphQLNamedType] = {type_.name: type_ for type_ in types}
        for type_ in gr_types:
            if not should_include(type_):
                continue
            if type_.name in type_map:
                raise ValueError(f"Type {type_.name} already exists")
            type_map[type_.name] = type_
            types.append(type_)
        return types

    def merge_object_types(self, sb_type: GraphQLObjectType | None, gr_type: GraphQLObjectType | None) -> GraphQLObjectType:
        assert sb_type is not None
        assert gr_type is not None
        fields = self.merge_fields(sb_type.fields, gr_type.fields)
        return GraphQLObjectType(
            name=sb_type.name or gr_type.name,
            fields=fields,
        )

    def merge_directives(
        self, sb_directives: Sequence[GraphQLDirective], gr_directives: Sequence[GraphQLDirective]
    ) -> list[GraphQLDirective]:
        from graphql.type.directives import specified_directives

        directives: list[GraphQLDirective] = list(sb_directives)

        def should_merge(directive: GraphQLDirective) -> bool:
            for d in directives:
                if d.name != directive.name:
                    continue
                for sd in specified_directives:
                    if directive.name == sd.name:
                        return False
                if set(d.locations) & set(directive.locations):
                    raise ValueError(f"Directive {directive.name} already exists")
            return True

        for directive in gr_directives:
            if not should_merge(directive):
                continue
            directives.append(directive)
        return directives

    def merge_fields(self, sb_fields: dict[str, GraphQLField], gr_fields: dict[str, GraphQLField]) -> dict[str, GraphQLField]:
        fields: dict[str, GraphQLField] = {}
        for name, field in sb_fields.items():
            if name in fields:
                raise ValueError(f"Field {name} already exists in {sb_fields}")
            fields[name] = field
        for name, field in gr_fields.items():
            if name in fields:
                raise ValueError(f"Field {name} already exists in {gr_fields}")
            fields[name] = field
        return fields


class StrawberryCompatibleTypeMap(GrapheneTypeMap):
    def __init__(
        self,
        sb_schema: strawberry.Schema,
        query: type[graphene.ObjectType] | None = None,
        mutation: type[graphene.ObjectType] | None = None,
        subscription: type[graphene.ObjectType] | None = None,
        types: Sequence[type[graphene.ObjectType]] | None = None,
        auto_camelcase: bool = True,
    ):
        self.sb_schema = sb_schema
        gql_schema = sb_schema._schema
        super().__init__(query=query, mutation=mutation, subscription=subscription, types=types, auto_camelcase=auto_camelcase)  # type: ignore
        mutation_type = self.mutation
        if gql_schema.mutation_type:
            for name, field in gql_schema.mutation_type.fields.items():
                if name in mutation_type.fields:
                    raise ValueError(f"Field {name} already exists in {mutation_type}")
                mutation_type.fields[name] = field
        for type_ in gql_schema.type_map.values():
            if not is_abstract_type(type_):
                continue
            imp_types = gql_schema.get_possible_types(cast(GraphQLAbstractType, type_))
            for imp_type in imp_types:
                if imp_type.name not in self:
                    self.types.append(imp_type)

    def add_type(self, type_: type[graphene.ObjectType] | type) -> GraphQLType:
        if has_object_definition(type_):
            name = self.sb_schema.config.name_converter.from_type(type_.__strawberry_definition__)
            ct = self.sb_schema.schema_converter.type_map[name]
            if ct is not None:
                if name in self:
                    return self[name]
                graphql_type = ct.implementation
                self[name] = graphql_type
                return graphql_type
        return super().add_type(type_)  # type: ignore


class CombinedSchema(graphene.Schema):
    def __init__(
        self,
        sb_schema: strawberry.Schema,
        query: type[graphene.ObjectType] | None = None,
        mutation: type[graphene.ObjectType] | None = None,
        subscription: type[graphene.ObjectType] | None = None,
        types: Sequence[type[graphene.ObjectType]] | None = None,
        directives: Sequence[GraphQLDirective] | None = None,
        auto_camelcase: bool = True,
    ):
        self.query = query
        self.mutation = mutation
        self.subscription = subscription
        type_map = StrawberryCompatibleTypeMap(
            sb_schema, query, mutation, subscription, types, auto_camelcase=auto_camelcase
        )
        if directives is None:
            directives = ()
        sb_directives = sb_schema._schema.directives
        # graphql_types = type_map.types
        # for name, type_ in sb_schema._schema.type_map.items():
        #     if name in type_map:
        #         continue
        #     type_map.add_type(type_)
        self.graphql_schema = GraphQLSchema(
            type_map.query,
            type_map.mutation,
            type_map.subscription,
            type_map.types,
            (*directives, *sb_directives),
        )
