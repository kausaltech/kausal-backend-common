from __future__ import annotations

from typing import TYPE_CHECKING, Any

import graphene
from django.apps import apps
from django.contrib.contenttypes.fields import GenericForeignKey
from django.db import models
from django.utils.functional import lazy
from django.utils.translation import gettext_lazy as _
from wagtail import blocks

from grapple.models import GraphQLString

from kausal_common.const import IS_PATHS, IS_WATCH
from kausal_common.graphene.registry import register_graphene_interface

if TYPE_CHECKING:
    if IS_WATCH:
        from aplans.graphql_types import GQLInfo
    elif IS_PATHS:
        from paths.graphql_types import PathsGQLInfo as GQLInfo


def get_field_label(model: type[models.Model], field_name: str) -> str | None:
    if not apps.ready:
        return 'label'
    field = model._meta.get_field(field_name)
    if isinstance(field, models.ForeignObjectRel | GenericForeignKey):
        # It's a relation field
        related_model = field.related_model
        if isinstance(related_model, str):
            label = str(model._meta.verbose_name_plural).capitalize()
        else:
            label = str(related_model._meta.verbose_name_plural).capitalize()
    else:
        label = str(field.verbose_name).capitalize()
    return label


lazy_field_label = lazy(get_field_label, str)


class ListColumnFieldBlock(blocks.StructBlock):
    field_label = blocks.CharBlock(
        required=False,
        help_text=_('Heading to show instead of the default'),
        default='',
        label=_('Field label'),
    )

    field_help_text = blocks.CharBlock(
        required=False,
        help_text=_('Help text for the field to be shown in the UI'),
        default='',
        label=_('Help text'),
    )

    graphql_fields = [
        GraphQLString('field_label'),
        GraphQLString('field_help_text'),
    ]

    def get_admin_text(self):
        return _('Content block: %(label)s') % dict(label=self.label)


class FieldBlockMetaData(graphene.ObjectType[Any]):
    restricted = graphene.Boolean()
    hidden = graphene.Boolean()

    @staticmethod
    def resolve_restricted(root: dict[str, bool], _info: GQLInfo) -> bool:
        return root['restricted']

    @staticmethod
    def resolve_hidden(root: dict[str, bool], _info: GQLInfo) -> bool:
        return root['hidden']


class FieldBlockMetaField:
    meta = graphene.Field(FieldBlockMetaData)


@register_graphene_interface
class FieldBlockMetaInterface(graphene.Interface['Any']):
    meta = graphene.Field(FieldBlockMetaData)

    @staticmethod
    def resolve_meta(root, info: GQLInfo) -> dict[str, bool]:
        if IS_PATHS:
            return {
                'restricted': False,
                'hidden': False,
            }

        if IS_WATCH:
            from aplans.graphql_types import get_plan_from_context

            attribute_type = root.value.get('attribute_type') if root.value else None
            user = info.context.user
            plan = get_plan_from_context(info)

            restricted = hidden = False
            if attribute_type:
                # TODO: implement for builtin fields as well
                hidden = not attribute_type.is_instance_visible_for(user, plan, None)
                restricted = attribute_type.instances_visible_for != attribute_type.VisibleFor.PUBLIC
            return {
                'restricted': restricted,
                'hidden': hidden,
            }
        return {
            'restricted': False,
            'hidden': False,
        }
