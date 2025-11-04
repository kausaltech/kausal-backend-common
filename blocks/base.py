from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar, Protocol

import graphene
from django.apps import apps
from django.contrib.contenttypes.fields import GenericForeignKey
from django.db import models
from django.utils.functional import lazy
from django.utils.translation import gettext_lazy as _
from wagtail import blocks

from grapple.models import GraphQLField, GraphQLString

from kausal_common.blocks.fields import FieldBlockMetaInterface

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Sequence

    from django.db.models import Model
    from django_stubs_ext import StrOrPromise
    from wagtail.blocks.base import BlockMeta
    from wagtail.blocks.struct_block import StructValue

    class BlockMetaWithFieldName(Protocol, BlockMeta):  # pyright: ignore
        field_name: str
else:
    class BlockMetaWithFieldName:
        pass


class DashboardColumnInterface(graphene.Interface[Any]):
    column_label = graphene.String()
    column_help_text = graphene.String()

    @staticmethod
    def resolve_source_field(root: StructValue[ColumnBlockBase], _info) -> str | None:
        return root.block.meta.field_name


class ColumnBlockBase(blocks.StructBlock):
    column_label = blocks.CharBlock(
        required=False, label=_("Label"), help_text=_("Label for the column to be used instead of the default"),
    )
    column_help_text = blocks.CharBlock(
        required=False, label=_("Help text"), help_text=_("Help text for the column to be shown in the UI"),
    )
    source_field: graphene.Field

    graphql_fields = [
        GraphQLString('column_label'),
        GraphQLString('column_help_text'),
    ]

    graphql_interfaces: ClassVar[Sequence[type[graphene.Interface[Any]]]] = [DashboardColumnInterface]

    MUTABLE_META_ATTRIBUTES = [
        *blocks.StructBlock.MUTABLE_META_ATTRIBUTES,
        'field_name',
    ]

    meta: BlockMetaWithFieldName

    class Meta:
        field_name: str | None = None


def get_field_label(model: type[Model], field_name: str) -> str | None:
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


def static_block_to_struct_compat(values: list[Any]):
    li = list(values)
    if len(li) == 1 and li[0] is None:
        values = [{}]
    return values


class GeneralFieldBlockInterface(graphene.Interface[Any]):
    source_field: graphene.Field

    field_label = graphene.String()
    field_help_text = graphene.String()

    graphql_interfaces = (FieldBlockMetaInterface, )

    @staticmethod
    def resolve_source_field(root: StructValue[GeneralFieldBlockBase[Any]], _info) -> str | None:
        return root.block.meta.field_name


class GeneralFieldBlockBase[M: BlockMetaWithFieldName = BlockMetaWithFieldName](blocks.StructBlock[M]):
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

    graphql_fields: list[Callable[[], GraphQLField] | GraphQLField] = [
        GraphQLString('field_label'),
        GraphQLString('field_help_text'),
    ]
    graphql_interfaces: ClassVar[Sequence[type[graphene.Interface[Any]]]]

    MUTABLE_META_ATTRIBUTES: ClassVar[Iterable[str]] = [
        *blocks.StructBlock.MUTABLE_META_ATTRIBUTES,
        'field_name',
    ]

    meta: M

    class Meta:
        field_name: str | None = None

    # Workaround for migration from StaticBlock to StructBlock
    def bulk_to_python(self, values):
        values = static_block_to_struct_compat(values)
        return super().bulk_to_python(values)


class ContentBlockBase(GeneralFieldBlockBase):
    def get_admin_text(self):
        return _('Content block: %(label)s') % dict(label=self.meta.label)


class FilterBlockInterface(GeneralFieldBlockInterface):
    show_all_label = graphene.String()


class FilterBlockBase(GeneralFieldBlockBase):
    show_all_label = blocks.CharBlock(required=False, label=_("Label for 'show all'"))

    graphql_fields = [
        *GeneralFieldBlockBase.graphql_fields,
        GraphQLString('show_all_label'),
    ]

    def get_admin_text(self) -> StrOrPromise:
        return _("Filter: %(filter_label)s") % dict(filter_label=self.meta.label)
