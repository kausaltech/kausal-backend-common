from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

from django import forms
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ImproperlyConfigured
from django.db.models import Count
from django.db.models.functions import Coalesce
from django.utils.translation import gettext_lazy as _, ngettext
from wagtail.admin.admin_url_finder import AdminURLFinder
from wagtail.admin.forms.models import WagtailAdminModelForm
from wagtail.admin.panels import FieldPanel
from wagtail.admin.ui.tables import BulkActionsCheckboxColumn, Column
from wagtail.admin.views.generic.usage import TitleColumn, UsageView
from wagtail.log_actions import log
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import CreateView, DeleteView, IndexView

from kausal_common.admin_site.permissioned_views import PermissionedViewSet
from kausal_common.const import IS_PATHS, IS_WATCH

from .config import dataset_config
from .models import Dataset, DataSource

if TYPE_CHECKING:
    from django.db.models.base import Model

    from users.models import User


class DataSourceForm(WagtailAdminModelForm[DataSource]):
    url = forms.URLField(required=False, assume_scheme='https')

    class Meta:
        model = DataSource
        exclude = ['scope_content_type', 'scope_id']


class DataSourceCreateView(CreateView[DataSource, DataSourceForm]):
    def save_instance(self):
        user = cast('User', self.request.user)
        default_scope_app, default_scope_model = dataset_config.DATA_SOURCE_DEFAULT_SCOPE_CONTENT_TYPE

        scope_content_type = ContentType.objects.get(app_label=default_scope_app, model=default_scope_model)
        scope_id: int
        if IS_PATHS and default_scope_app == 'nodes':
            from paths.context import realm_context

            active_instance = realm_context.get().realm
            scope_id = active_instance.pk
        elif IS_WATCH and default_scope_app == 'actions':
            active_plan = user.get_active_admin_plan()
            scope_id = active_plan.pk
        else:
            raise ImproperlyConfigured()

        instance = self.form.save(commit=False)

        instance.scope_content_type = scope_content_type
        instance.scope_id = scope_id
        instance.save()
        log(instance=instance, action='wagtail.create', content_changed=True)
        return instance


@dataclass(frozen=True)
class DataSourceCitation:
    """One dataset citing a data source: at the dataset level, from its data points, or both."""

    dataset: Dataset
    data_points: int
    dataset_level: bool


class DataSourceUsage:
    """
    Where a data source is cited, in the shape Wagtail's delete view asks of its usage.

    Read from the ``PROTECT``ed ``DatasetSourceReference.data_source`` foreign key rather
    than from Wagtail's reference index. No StreamField can hold a data source, so the index
    would only be a copy of this one relation, kept current by per-row ``post_save`` signals
    that every bulk import skips.
    """

    def __init__(self, source: DataSource):
        rows = (
            source.references
            .annotate(cited_by=Coalesce('dataset_id', 'data_point__dataset_id'))
            .values('cited_by')
            .annotate(data_points=Count('data_point'), dataset_level=Count('dataset'))
            .order_by()
        )
        datasets = Dataset.objects.select_related('schema').in_bulk([row['cited_by'] for row in rows])
        self.citations = [
            DataSourceCitation(
                dataset=datasets[row['cited_by']],
                data_points=row['data_points'],
                dataset_level=row['dataset_level'] > 0,
            )
            for row in rows
        ]

    def count(self) -> int:
        return len(self.citations)

    @property
    def is_protected(self) -> bool:
        return bool(self.citations)


class DataSourceUsageView(UsageView[DataSource]):
    """One row per citing dataset, linking to the dataset rather than to each reference."""

    def get_queryset(self):
        return DataSourceUsage(self.object).citations

    columns = [
        TitleColumn('name', label=_('Dataset'), accessor='label', get_url=lambda row: row['edit_url']),
        Column('cited_by', label=_('Cited by'), accessor='cited_by'),
    ]

    def get_table(self, object_list, **kwargs):
        url_finder = AdminURLFinder(self.request.user)
        results = []
        for citation in object_list:
            edit_url = url_finder.get_edit_url(citation.dataset)
            parts: list[str] = []
            if citation.dataset_level:
                parts.append(str(_('the dataset')))
            if citation.data_points:
                parts.append(
                    ngettext('%(count)d data point', '%(count)d data points', citation.data_points)
                    % {'count': citation.data_points}
                )
            results.append({
                'object': citation.dataset,
                'label': str(citation.dataset) if edit_url else _('(Private dataset)'),
                'edit_url': edit_url,
                'edit_link_title': _('Edit dataset') if edit_url else None,
                'cited_by': ', '.join(parts),
            })
        return super(UsageView, self).get_table(results, **kwargs)


class DataSourceDeleteView(DeleteView[DataSource]):
    def get_usage(self):
        if not self.usage_url:
            return None
        return DataSourceUsage(self.object)


class DataSourceIndexView(IndexView[DataSource]):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Hide the bulk delete to avoid ProtectedError when deleting referenced datasources.
        # Remove this if usage checks are implemented for bulk actions.
        self.columns = [c for c in super().columns if not isinstance(c, BulkActionsCheckboxColumn)]


class DataSourceViewSet(PermissionedViewSet[DataSource, DataSourceForm]):
    model = DataSource
    menu_label = _('Data sources')
    icon = 'doc-full'
    menu_order = 11
    add_to_settings_menu = True
    form_class = DataSourceForm
    copy_view_enabled = False
    add_view_class = DataSourceCreateView  # type: ignore[assignment]
    # See DataSourceUsage: the usage and delete views read the foreign key directly.
    add_to_reference_index = False
    usage_view_class = DataSourceUsageView  # type: ignore[assignment]  # pyright: ignore[reportAssignmentType]
    index_view_class = DataSourceIndexView  # type: ignore[assignment]
    delete_view_class = DataSourceDeleteView  # type: ignore[assignment]
    panels = [
        FieldPanel('name'),
        FieldPanel('edition'),
        FieldPanel('authority'),
        FieldPanel('description'),
        FieldPanel('url'),
    ]

    def get_queryset(self, request):
        qs = DataSource.objects.all()
        user = cast('User', request.user)
        default_scope_app, default_scope_model = dataset_config.DATA_SOURCE_DEFAULT_SCOPE_CONTENT_TYPE
        active_obj: Model
        if IS_PATHS:
            from paths.context import realm_context

            active_obj = realm_context.get().realm
        elif IS_WATCH:
            active_obj = user.get_active_admin_plan()
        else:
            raise ImproperlyConfigured()
        if not active_obj:
            return DataSource.objects.none()

        scope_content_type = ContentType.objects.get(app_label=default_scope_app, model=default_scope_model)
        return qs.filter(scope_content_type=scope_content_type, scope_id=active_obj.pk)


register_snippet(DataSourceViewSet)
