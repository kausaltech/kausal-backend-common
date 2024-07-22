from __future__ import annotations

import os

import graphene

from kausal_common.deployment import get_deployment_build_id, get_deployment_git_rev


class ServerDeployment(graphene.ObjectType):
    build_id = graphene.String()
    git_revision = graphene.String()
    deployment_type = graphene.String()

    def resolve_build_id(self, info):
        return get_deployment_build_id()

    def resolve_git_revision(self, info):
        return get_deployment_git_rev()

    def resolve_deployment_type(self, info):
        return os.environ.get('DEPLOYMENT_TYPE', None)


class Query(graphene.ObjectType):
    server_deployment = graphene.Field(ServerDeployment, required=True)

    def resolve_server_deployment(self, info):
        return ServerDeployment()
