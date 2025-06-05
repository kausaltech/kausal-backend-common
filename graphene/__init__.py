from __future__ import annotations

import functools
import re
from typing import TYPE_CHECKING, Any, Generic
from typing_extensions import TypeVar

import graphene
from django.db.models import Model
from django.db.models.constants import LOOKUP_SEP
from graphene.utils.trim_docstring import trim_docstring
from graphene_django import DjangoObjectType
from modeltrans.translator import get_i18n_field

import graphene_django_optimizer as gql_optimizer
from graphene_pydantic import PydanticObjectType

from kausal_common.i18n.helpers import get_language_from_default_language_field
from kausal_common.models.permissions import PermissionedModel, UserPermissions, get_user_permissions_for_instance
from kausal_common.strawberry.context import GraphQLContext
from kausal_common.users import is_authenticated

if TYPE_CHECKING:
    from collections.abc import Iterable
    from typing import type_check_only

    from django.http import HttpRequest
    from graphene import Field, Interface
    from graphene_django.types import DjangoObjectTypeOptions
    from graphql import GraphQLResolveInfo
    from modeltrans.fields import TranslationField

    from kausal_common.const import IS_PATHS
    from kausal_common.users import UserOrAnon

    @type_check_only
    class GQLContext(HttpRequest):
        user: UserOrAnon  # type: ignore[override]
        graphql_query_language: str

    if IS_PATHS:
        @type_check_only
        class GQLInfo(GraphQLResolveInfo):
            context: GraphQLContext
    else:
        @type_check_only
        class GQLInfo(GraphQLResolveInfo):
            context: GQLContext  # type: ignore[override]


class ModelWithI18n(Model):
    i18n: TranslationField

    class Meta:
        abstract = True


def get_i18n_field_with_fallback(field_name: str, obj: ModelWithI18n, info: GQLInfo):
    i18n_field = get_i18n_field(obj._meta.model)
    assert i18n_field is not None
    fallback_value = getattr(obj, field_name)
    fallback_lang = get_language_from_default_language_field(obj, i18n_field)  # pyright: ignore
    fallback = (fallback_value, fallback_lang)

    active_language = getattr(info.context, '_graphql_query_language', None)
    if not active_language:
        return fallback

    active_language = active_language.lower().replace('-', '_')

    i18n_values = getattr(obj, i18n_field.name)
    if i18n_values is None or active_language == fallback_lang:
        return fallback

    lang_field_name = '%s_%s' % (field_name, active_language)
    trans_value = i18n_values.get(lang_field_name)
    if not trans_value:
        return fallback

    trans_value = i18n_values.get(lang_field_name, getattr(obj, field_name))
    return trans_value, active_language


def resolve_i18n_field(field_name, obj, info):
    value, lang = get_i18n_field_with_fallback(field_name, obj, info)
    return value


M = TypeVar('M', bound=Model)


class DjangoNodeMeta:
    model: type[Model]
    name: str
    description: str
    fields: dict[str, Field] | Iterable[str]
    interfaces: Iterable[type[Interface]]


def _get_user(info: GQLInfo) -> UserOrAnon:
    if isinstance(info.context, GraphQLContext):
        user = info.context.get_user()
    else:
        user = info.context.user
    return user


def resolve_user_roles(obj: Model, info: GQLInfo) -> list[str]:
    assert isinstance(obj, PermissionedModel)
    user = _get_user(info)
    if user is None or not is_authenticated(user):
        return []

    roles = user.perms.get_roles_for_instance(obj)
    if roles is None:
        return []
    return [role.id for role in roles]


class UserPermissionsType(PydanticObjectType):
    class Meta:
        model = UserPermissions
        name = 'UserPermissions'


def resolve_user_permissions(obj: PermissionedModel, info: GQLInfo) -> UserPermissions:
    assert isinstance(obj, PermissionedModel)
    user = _get_user(info)
    return get_user_permissions_for_instance(user, obj)


UserRolesField = graphene.List(graphene.NonNull(graphene.String), required=False)


class DjangoNode(DjangoObjectType, Generic[M]):
    user_permissions = graphene.Field(UserPermissionsType, resolver=resolve_user_permissions)
    user_roles = graphene.Field(UserRolesField, resolver=resolve_user_roles)
    _meta: DjangoObjectTypeOptions

    @classmethod
    def _resolve_i18n_fields(cls) -> None:
        # Set default resolvers for i18n fields
        i18n_field = get_i18n_field(cls._meta.model)
        if i18n_field is None:
            return
        fields = cls._meta.fields
        for translated_field_name in i18n_field.fields:
            # translated_field_name is only in fields if it is in *Node.Meta.fields
            field = fields.get(translated_field_name)
            if field is not None and field.resolver is None and not hasattr(cls, 'resolve_%s' % translated_field_name):
                resolver = functools.partial(resolve_i18n_field, translated_field_name)
                only = [translated_field_name, i18n_field.name]
                select_related = []
                default_language_field = i18n_field.default_language_field
                if default_language_field:
                    parsed_default_language_field = default_language_field.split(LOOKUP_SEP)
                    only.append(default_language_field)
                    if len(parsed_default_language_field) > 1:
                        related_path = parsed_default_language_field[:-1]
                        select_related.append(LOOKUP_SEP.join(related_path))
                hints = dict(
                    only=only,
                    select_related=select_related,
                )
                apply_hints = gql_optimizer.resolver_hints(**hints)
                field.resolver = apply_hints(resolver)

    @classmethod
    def __init_subclass_with_meta__(cls, **kwargs: Any) -> None:  # type: ignore[override]
        if 'name' not in kwargs:
            # Remove the trailing 'Node' from the object types
            name = cls.__name__
            if name.endswith('Type'):
                name = re.sub(r'Type$', '', name)
            elif name.endswith('Node'):
                name = re.sub(r'Node$', '', name)
            kwargs['name'] = name

        model: type[M] = kwargs['model']
        assert model.__doc__ is not None
        is_autogen = re.match(r'^\w+\([\w_, ]+\)$', model.__doc__)
        if 'description' not in kwargs and not cls.__doc__ and not is_autogen:
            kwargs['description'] = trim_docstring(model.__doc__)

        super().__init_subclass_with_meta__(**kwargs)
        cls._resolve_i18n_fields()

        from kausal_common.models.permissions import PermissionedModel
        if not issubclass(model, PermissionedModel):
            fields = cls._meta.fields
            if 'allowed_actions' in cls._meta.fields:
                del fields['allowed_actions']

    if TYPE_CHECKING:
        Meta: Any
    else:
        class Meta:
            abstract = True
