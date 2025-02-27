from __future__ import annotations

from django.utils.translation import gettext_lazy as _
from wagtail.admin.panels.field_panel import FieldPanel
from wagtail.admin.panels.inline_panel import InlinePanel
from wagtail.snippets.views.snippets import SnippetViewSet

from kausal_common.datasets.models import DatasetSchema


class DatasetSchemaViewSet(SnippetViewSet):
    model = DatasetSchema
    icon = 'table'
    add_to_admin_menu = True
    menu_order = 200
    menu_label = _('Dataset schemas')
    list_display = ('name_i18n',)
    search_fields = ['name_i18n']

    panels = [
        FieldPanel(
            'name',
            heading=_("Name"),
            help_text=_("Descriptive name of the dataset schema"),
        ),
        FieldPanel(
            'unit',
            heading=_("Unit"),
            help_text=_("Unit of the dataset schema"),
        ),
        FieldPanel(
            'time_resolution',
            heading=_("Time Resolution"),
        ),
        FieldPanel(
            'start_date',
            heading=_("Start Date"),
        ),
        InlinePanel(
            'dimensions',
            heading=_("Dimensions"),
            help_text=_("Used when metrics are tracked for multiple categories"),
            panels=[
                FieldPanel('dimension'),
            ]
        ),
    ]
