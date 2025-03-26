from __future__ import annotations

from typing import TYPE_CHECKING, cast

import graphene
from django.conf import settings
from graphql import GraphQLError

from kausal_common.deployment.types import is_development_environment
from kausal_common.models.roles import role_registry

from users.models import User
from users.schema import UserType

if TYPE_CHECKING:
    from kausal_common.graphene import GQLInfo


# for instance-specific roles; KP's framework roles don't have anything to do with this
class RoleInput(graphene.InputObjectType):
    id = graphene.String(required=True)
    object = graphene.String(required=True)


class RegisterUser(graphene.Mutation):
    class Arguments:
        email = graphene.String(required=True)
        password = graphene.String(required=True)
        roles = graphene.List(RoleInput)

    user = graphene.Field(UserType)

    def mutate(self, info: GQLInfo, email: str, password: str, roles: list[RoleInput]):
        if not settings.DANGEROUSLY_ENABLE_REGISTER_USER_MUTATION:
            raise GraphQLError("This mutation is not enabled", nodes=info.field_nodes)
        if not is_development_environment():
            raise GraphQLError("This mutation is not allowed in non-development environments", nodes=info.field_nodes)
        email = email.strip().lower()
        if User.objects.filter(email=email).exists():
            raise GraphQLError("A user with that email already exists", nodes=info.field_nodes)
        user = User(email=email)
        user.set_password(password)
        user.save()
        for role_input in roles:
            role_id = cast(str, role_input.id)
            role = role_registry.get_role(role_id)
            role_obj_identifier = cast(str, role_input.object)
            obj = role.model.objects.get(identifier=role_obj_identifier)
            role.assign_user(obj, user)
        return RegisterUser(user=user)


class DeleteUser(graphene.Mutation):
    class Arguments:
        email = graphene.String(required=True)

    ok = graphene.Boolean()

    def mutate(self, info: GQLInfo, email: str):
        if not settings.DANGEROUSLY_ENABLE_DELETE_USER_MUTATION:
            raise GraphQLError("This mutation is not enabled", nodes=info.field_nodes)
        if not is_development_environment():
            raise GraphQLError("This mutation is not allowed in non-development environments", nodes=info.field_nodes)
        email = email.strip().lower()
        User.objects.get(email=email).delete()
        return DeleteUser(ok=True)


class Mutations(graphene.ObjectType):
    register_user = RegisterUser.Field()
    delete_user = DeleteUser.Field()
