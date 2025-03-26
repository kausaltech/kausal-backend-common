from graphene_django import DjangoObjectType
from kausal_common.datasets.models import (
    Dataset,
    DatasetSchemaScope,
    DimensionScope,
)

import graphene


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
    def resolve_scope(root: DimensionScope, info):
        return root.scope


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
    def resolve_scope(root: DatasetSchemaScope, info):
        return root.scope


class DatasetSchemaScopeTypeNode(graphene.Union):
    class Meta:
        abstract = True


class DatasetNode(DjangoObjectType):
    scope = graphene.Field(lambda: DatasetScopeTypeNode)

    class Meta:
        abstract = True

    @staticmethod
    def resolve_scope(root: Dataset, info):
        return root.scope


class DatasetScopeTypeNode(graphene.Union):
    class Meta:
        abstract = True


class DatasetSchemaNode(DjangoObjectType):
    class Meta:
        abstract = True


class DatasetMetricNode(DjangoObjectType):
    class Meta:
        abstract = True
