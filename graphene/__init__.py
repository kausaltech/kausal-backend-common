from __future__ import annotations

import functools
import re
import typing
from typing import Any, Generic, Type, TypeVar

import graphene_django_optimizer as gql_optimizer
from django.contrib.auth.models import AnonymousUser
from django.db.models import Model
from django.db.models.constants import LOOKUP_SEP
from graphene.utils.trim_docstring import trim_docstring
from graphene_django import DjangoObjectType
from graphene_django.types import DjangoObjectTypeOptions
from graphql import GraphQLResolveInfo
from graphql.language.ast import OperationDefinitionNode
from modeltrans.fields import TranslationField
from modeltrans.translator import get_i18n_field
from wagtail.models import WSGIRequest

from kausal_common.i18n.helpers import get_language_from_default_language_field
from users.models import User

UserOrAnon: typing.TypeAlias = 'User | AnonymousUser'


class GQLContext(WSGIRequest):
    user: UserOrAnon
    graphql_query_language: str


class GQLInfo(GraphQLResolveInfo):
    context: GQLContext
    operation: OperationDefinitionNode


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


class DjangoNode(DjangoObjectType, Generic[M]):
    _meta: DjangoObjectTypeOptions

    @classmethod
    def __init_subclass_with_meta__(cls, **kwargs: Any):
        if 'name' not in kwargs:
            # Remove the trailing 'Node' from the object types
            name = cls.__name__
            if name.endswith('Type'):
                name = re.sub(r'Type$', '', name)
            elif name.endswith('Node'):
                name = re.sub(r'Node$', '', name)
            kwargs['name'] = name

        model: Type[M] = kwargs['model']
        assert model.__doc__ is not None
        is_autogen = re.match(r'^\w+\([\w_, ]+\)$', model.__doc__)
        if 'description' not in kwargs and not cls.__doc__ and not is_autogen:
            kwargs['description'] = trim_docstring(model.__doc__)

        super().__init_subclass_with_meta__(**kwargs)

        # Set default resolvers for i18n fields
        i18n_field = get_i18n_field(cls._meta.model)
        if i18n_field is not None:
            fields = cls._meta.fields
            for translated_field_name in i18n_field.fields:
                # translated_field_name is only in fields if it is in *Node.Meta.fields
                field = fields.get(translated_field_name)
                if field is not None and field.resolver is None and not hasattr(cls, 'resolve_%s' % translated_field_name):
                    resolver = functools.partial(resolve_i18n_field, translated_field_name)
                    only = [translated_field_name, i18n_field.name]
                    select_related=[]
                    default_language_field = i18n_field.default_language_field
                    if default_language_field:
                        parsed_default_language_field = default_language_field.split(LOOKUP_SEP)
                        only.append(default_language_field)
                        if len(parsed_default_language_field) > 1:
                            related_path = parsed_default_language_field[:-1]
                            select_related.append(LOOKUP_SEP.join(related_path))
                    hints = dict(
                        only=only,
                        select_related=select_related
                    )
                    apply_hints = gql_optimizer.resolver_hints(**hints)
                    field.resolver = apply_hints(resolver)

    class Meta:
        abstract = True
