from __future__ import annotations

from typing import TYPE_CHECKING

import graphene

import graphene_django_optimizer as gql_optimizer

from kausal_common.graphene import DjangoNode

from .forms import NodeForm

if TYPE_CHECKING:
    from orgs.models import Organization, OrganizationQuerySet


class OrganizationForm(NodeForm):
    class Meta:
        abstract = True


class OrganizationClassNode(DjangoNode):
    class Meta:
        abstract = True



class OrganizationNode(DjangoNode):
    ancestors = graphene.List('orgs.schema.OrganizationNode')
    descendants = graphene.List('orgs.schema.OrganizationNode')
    parent = graphene.Field('orgs.schema.OrganizationNode', required=False)
    path = graphene.String(required=True)

    class Meta:
        abstract = True

    @staticmethod
    def resolve_ancestors(root: Organization, info) -> OrganizationQuerySet:
        return root.get_ancestors()

    @staticmethod
    def resolve_descendants(parent: Organization, info) -> OrganizationQuerySet:
        return parent.get_descendants()

    @gql_optimizer.resolver_hints(
        only=('path', 'depth'),
    )
    @staticmethod
    def resolve_parent(parent: Organization, info) -> Organization | None:
        return parent.get_parent()
