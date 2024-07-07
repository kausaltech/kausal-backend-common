import os
import graphene


class ServerDeployment(graphene.ObjectType):
    build_id = graphene.String()
    git_revision = graphene.String()
    deployment_type = graphene.String()

    def resolve_build_id(self, info):
        return os.environ.get('BUILD_ID', None)

    def resolve_git_revision(self, info):
        return os.environ.get('GIT_REV', None)

    def resolve_deployment_type(self, info):
        return os.environ.get('DEPLOYMENT_TYPE', None)


class Query(graphene.ObjectType):
    server_deployment = graphene.Field(ServerDeployment, required=True)

    def resolve_server_version(self, info):
        return ServerDeployment()
