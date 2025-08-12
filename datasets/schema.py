from __future__ import annotations

from typing import TYPE_CHECKING, cast

import graphene
from graphene_django import DjangoObjectType

if TYPE_CHECKING:
    from kausal_common.datasets.models import (
        Dataset,
        DatasetSchemaScope,
        DatasetScopeType,
        DimensionScope,
        DimensionScopeType,
    )


class DimensionNode(DjangoObjectType):
    class Meta:
        abstract = True


class DimensionCategoryNode(DjangoObjectType):
    class Meta:
        abstract = True


class DatasetSchemaDimensionNode(DjangoObjectType):
    class Meta:
        abstract = True


class DimensionScopeNode(DjangoObjectType):
    scope = graphene.Field(lambda: DimensionScopeTypeNode)

    class Meta:
        abstract = True

    @staticmethod
    def resolve_scope(root: DimensionScope, info) -> DimensionScopeType:
        return cast('DimensionScopeType', root.scope)


class DimensionScopeTypeNode(graphene.Union):
    class Meta:
        abstract = True  # Make it abstract


class DataPointNode(DjangoObjectType):
    value = graphene.Float()

    class Meta:
        abstract = True


class DatasetSchemaScopeNode(DjangoObjectType):
    scope = graphene.Field(lambda: DatasetSchemaScopeTypeNode)

    class Meta:
        abstract = True

    @staticmethod
    def resolve_scope(root: DatasetSchemaScope, info) -> DatasetScopeType:
        return cast('DatasetScopeType', root.scope)


class DatasetSchemaScopeTypeNode(graphene.Union):
    class Meta:
        abstract = True


class DatasetNode(DjangoObjectType):
    scope = graphene.Field(lambda: DatasetScopeTypeNode)

    class Meta:
        abstract = True

    @staticmethod
    def resolve_scope(root: Dataset, info) -> DatasetScopeType:
        return cast('DatasetScopeType', root.scope)


class DatasetScopeTypeNode(graphene.Union):
    class Meta:
        abstract = True


class DatasetSchemaNode(DjangoObjectType):
    class Meta:
        abstract = True


class DatasetMetricNode(DjangoObjectType):
    class Meta:
        abstract = True
