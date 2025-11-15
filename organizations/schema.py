from __future__ import annotations

from typing import TYPE_CHECKING, Any

import graphene

import graphene_django_optimizer as gql_optimizer

from kausal_common.graphene import DjangoNode
from kausal_common.graphene.graphql_helpers import (
    CreateModelInstanceMutation,
    DeleteModelInstanceMutation,
    UpdateModelInstanceMutation,
)
from kausal_common.organizations.models import BaseOrganization

from .forms import NodeForm

if TYPE_CHECKING:
    from orgs.models import Organization, OrganizationClass, OrganizationQuerySet


class OrganizationForm[OrgM: BaseOrganization[Any]](NodeForm[OrgM]):
    class Meta:
        abstract = True


class OrganizationClassNode(DjangoNode['OrganizationClass']):
    class Meta:
        abstract = True



class OrganizationNode[OrgM: BaseOrganization[Any]](DjangoNode[OrgM]):
    ancestors = graphene.List(graphene.NonNull('orgs.schema.OrganizationNode'), required=True)
    descendants = graphene.List('orgs.schema.OrganizationNode')
    parent = graphene.Field('orgs.schema.OrganizationNode', required=False)

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
    def resolve_parent(parent: OrgM, info) -> OrgM | None:
        return parent.get_parent()


class CreateOrganizationMutation(CreateModelInstanceMutation):
    class Meta:
        abstract = True


class UpdateOrganizationMutation(UpdateModelInstanceMutation):
    class Meta:
        abstract = True


class DeleteOrganizationMutation(DeleteModelInstanceMutation):
    class Meta:
        abstract = True



class Mutation(graphene.ObjectType):
    class Meta:
        abstract = True
