from __future__ import annotations
from django.utils.translation import gettext_lazy as _
from django.contrib.contenttypes.models import ContentType

from wagtail.admin.panels import FieldPanel
from wagtail.admin.forms.models import WagtailAdminModelForm
from wagtail.snippets.views.snippets import CreateView, SnippetViewSet
from wagtail.snippets.models import register_snippet
from wagtail.log_actions import log

from .models import DataSource
from .config import dataset_config


class DataSourceForm(WagtailAdminModelForm):
    class Meta:
        model = DataSource
        exclude = ['scope_content_type', 'scope_id']

class DataSourceCreateView(CreateView):
    def save_instance(self):
        user = self.request.user
        default_scope_app, default_scope_model = dataset_config.DATA_SOURCE_DEFAULT_SCOPE_CONTENT_TYPE
        scope_content_type = ContentType.objects.get(app_label=default_scope_app, model=default_scope_model)
        scope_id = None

        if default_scope_app == 'nodes':
            active_instance = user.get_active_instance() # type: ignore
            scope_id = active_instance.id
        elif default_scope_app == "actions":
            active_plan = user.get_active_admin_plan() # type: ignore
            scope_id = active_plan.id

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


    add_view_class = DataSourceCreateView
    panels = [
        FieldPanel('name'),
        FieldPanel('edition'),
        FieldPanel('authority'),
        FieldPanel('description'),
        FieldPanel('url'),
    ]

    def get_queryset(self, request):
        qs = DataSource.objects.all()
        user = request.user
        default_scope_app, default_scope_model = dataset_config.DATA_SOURCE_DEFAULT_SCOPE_CONTENT_TYPE
        active_obj = None
        if default_scope_app == 'nodes':
            active_obj = user.get_active_instance()
        elif default_scope_app == 'actions':
            active_obj = user.get_active_admin_plan()
        if not active_obj:
            return DataSource.objects.none()

        scope_content_type = ContentType.objects.get(app_label=default_scope_app, model=default_scope_model)
        return qs.filter(scope_content_type=scope_content_type, scope_id=active_obj.id)

register_snippet(DataSourceViewSet)
