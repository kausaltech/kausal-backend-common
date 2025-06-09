from __future__ import annotations


import graphene

import graphene_django_optimizer as gql_optimizer

from aplans.graphql_types import DjangoNode, register_django_node
from aplans.utils import public_fields

from actions.models import Plan
from .forms import NodeForm
from orgs.models import Organization, OrganizationQuerySet


class OrganizationForm(NodeForm):
    class Meta:
        abstract = True

class OrganizationClassNode(DjangoNode):
    class Meta:
        abstract = True


class OrganizationNode(DjangoNode):
    ancestors = graphene.List(lambda: OrganizationNode)
    descendants = graphene.List(lambda: OrganizationNode)
    parent = graphene.Field(lambda: OrganizationNode, required=False)

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


    class Meta:
        abstract = True


# class CreateOrganizationMutation(CreateModelInstanceMutation):
#     class Meta:
#         abstract = True


# class UpdateOrganizationMutation(UpdateModelInstanceMutation):
#     class Meta:
#         abstract = True


# class DeleteOrganizationMutation(DeleteModelInstanceMutation):
#     class Meta:
#         abstract = True


# class Mutation(graphene.ObjectType):
#     create_organization = CreateOrganizationMutation.Field()
#     update_organization = UpdateOrganizationMutation.Field()
#     delete_organization = DeleteOrganizationMutation.Field()
