"""Helper classes for formatting data as tables"""

from django.utils.translation import gettext_lazy as _
from wagtail.admin.ui.tables import DateColumn


class LastModifiedAtColumn(DateColumn):
    """
    Outputs the last_modified_at date annotation in human-readable format.

    Meant to be used to print the last update time of UserModifiableModels on Wagtail index views.

    Modified from wagtail.admin.ui.tables.UpdatedAtColumn.
    """

    def __init__(self, **kwargs):
        super().__init__(
            'last_modified_at',
            label=_("Last modified at"),
            sort_key="last_modified_at",
            **kwargs,
        )
