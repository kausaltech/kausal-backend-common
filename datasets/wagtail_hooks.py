from __future__ import annotations

from typing import TYPE_CHECKING, cast

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import gettext_lazy as _
from wagtail.admin.admin_url_finder import AdminURLFinder
from wagtail.admin.forms.models import WagtailAdminModelForm
from wagtail.admin.panels import FieldPanel
from wagtail.admin.views.generic.usage import UsageView
from wagtail.log_actions import log
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import CreateView

from kausal_common.admin_site.permissioned_views import PermissionedViewSet
from kausal_common.const import IS_PATHS, IS_WATCH

from .config import dataset_config
from .models import DataSource

if TYPE_CHECKING:
    from django.db.models.base import Model

    from users.models import User


class DataSourceForm(WagtailAdminModelForm[DataSource]):
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


class DataSourceUsageView(UsageView):
    """Custom usage view that links DatasetSourceReference to their parent Datasets."""

    def get_table(self, object_list, **kwargs):
        """Override to provide Dataset edit URLs for DatasetSourceReference objects."""
        url_finder = AdminURLFinder(self.request.user)
        results = []

        for object, references in object_list:
            from kausal_common.datasets.models import DatasetSourceReference

            row = {"object": object, "references": references}

            if isinstance(object, DatasetSourceReference):
                dataset = None
                if object.data_point:
                    dataset = object.data_point.dataset
                elif object.dataset:
                    dataset = object.dataset

                # Get the edit URL for the dataset
                if dataset:
                    row["edit_url"] = url_finder.get_edit_url(dataset)
                else:
                    row["edit_url"] = None

                if hasattr(object, 'get_admin_display_title'):
                    row["label"] = object.get_admin_display_title()
                else:
                    row["label"] = str(object)

                if row["edit_url"]:
                    row["edit_link_title"] = _("Edit dataset")
                else:
                    row["edit_link_title"] = None
            else:
                # Default behavior for other objects
                row["edit_url"] = url_finder.get_edit_url(object)
                if row["edit_url"] is None:
                    row["label"] = _("(Private %(object)s)") % {
                        "object": object._meta.verbose_name
                    }
                    row["edit_link_title"] = None
                else:
                    row["label"] = str(object)
                    row["edit_link_title"] = _("Edit this %(object)s") % {
                        "object": object._meta.verbose_name
                    }

            results.append(row)

        return super(UsageView, self).get_table(results, **kwargs)


class DataSourceViewSet(PermissionedViewSet):
    model = DataSource
    menu_label = _('Data sources')
    icon = 'doc-full'
    menu_order = 11
    add_to_settings_menu = True
    form_class = DataSourceForm
    copy_view_enabled = False
    add_view_class = DataSourceCreateView  # type: ignore[assignment]
    add_to_reference_index = True
    usage_view_class = DataSourceUsageView  # type: ignore[assignment]
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
