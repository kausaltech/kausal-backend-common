from __future__ import annotations

from typing import TYPE_CHECKING, cast

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import gettext_lazy as _
from wagtail.admin.forms.models import WagtailAdminModelForm
from wagtail.admin.panels import FieldPanel
from wagtail.log_actions import log
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import CreateView, SnippetViewSet

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
            active_instance = user.get_active_instance()
            scope_id = active_instance.pk
        elif IS_WATCH and default_scope_app == "actions":
            active_plan = user.get_active_admin_plan()
            scope_id = active_plan.pk
        else:
            raise ImproperlyConfigured()

        instance = self.form.save(commit=False)

        instance.scope_content_type = scope_content_type
        instance.scope_id = scope_id
        instance.save()
        log(instance=instance, action="wagtail.create", content_changed=True)
        return instance


class DataSourceViewSet(SnippetViewSet):
    model = DataSource
    menu_label = _('Data sources')
    icon = 'doc-full'
    menu_order = 11
    add_to_settings_menu = True
    form_class = DataSourceForm


    add_view_class = DataSourceCreateView  # type: ignore[override]
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
            active_obj = user.get_active_instance()
        elif IS_WATCH:
            active_obj = user.get_active_admin_plan()
        else:
            raise ImproperlyConfigured()

        if not active_obj:
            return DataSource.objects.none()

        scope_content_type = ContentType.objects.get(app_label=default_scope_app, model=default_scope_model)
        return qs.filter(scope_content_type=scope_content_type, scope_id=active_obj.pk)

register_snippet(DataSourceViewSet)
