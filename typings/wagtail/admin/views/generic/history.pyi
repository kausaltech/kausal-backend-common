from typing import ClassVar

from django.utils.functional import cached_property as cached_property
from django.views.generic import TemplateView
from django_stubs_ext import StrOrPromise
from wagtail.admin.filters import (
    DateRangePickerWidget as DateRangePickerWidget,
    MultipleUserFilter as MultipleUserFilter,
    WagtailFilterSet as WagtailFilterSet,
)
from wagtail.admin.ui.tables import Column as Column, DateColumn as DateColumn, UserColumn as UserColumn
from wagtail.admin.utils import get_latest_str as get_latest_str
from wagtail.admin.views.generic.base import (
    BaseListingView as BaseListingView,
    BaseObjectMixin as BaseObjectMixin,
    WagtailAdminTemplateMixin as WagtailAdminTemplateMixin,
)
from wagtail.admin.views.generic.permissions import PermissionCheckedMixin as PermissionCheckedMixin
from wagtail.admin.widgets.button import HeaderButton as HeaderButton
from wagtail.models import (
    BaseLogEntry as BaseLogEntry,
    DraftStateMixin as DraftStateMixin,
    PreviewableMixin as PreviewableMixin,
    Revision as Revision,
    RevisionMixin as RevisionMixin,
    TaskState as TaskState,
    WorkflowState as WorkflowState,
)

from _typeshed import Incomplete

def get_actions_for_filter(queryset): ...

class HistoryFilterSet(WagtailFilterSet):
    action: Incomplete
    user: Incomplete
    timestamp: Incomplete
    def __init__(self, *args, **kwargs) -> None: ...

class ActionColumn(Column):
    object: Incomplete
    url_names: Incomplete
    user_can_unschedule: Incomplete
    revision_enabled: Incomplete
    draftstate_enabled: Incomplete
    def __init__(self, *args, object, url_names, user_can_unschedule, **kwargs) -> None: ...  # noqa: A002
    @cached_property
    def cell_template_name(self): ...
    def get_status(self, instance, parent_context): ...
    def get_actions(self, instance, parent_context): ...
    def get_cell_context_data(self, instance, parent_context): ...

class LogEntryUserColumn(UserColumn):
    def __init__(self, name, **kwargs) -> None: ...
    def get_cell_context_data(self, instance, parent_context): ...

class HistoryView(PermissionCheckedMixin, BaseObjectMixin, BaseListingView):
    any_permission_required: Incomplete
    page_title: ClassVar[StrOrPromise]
    results_template_name: str
    header_icon: ClassVar[str]
    is_searchable: bool
    paginate_by: int
    filterset_class = HistoryFilterSet
    history_url_name: Incomplete
    history_results_url_name: Incomplete
    edit_url_name: Incomplete
    revisions_view_url_name: Incomplete
    revisions_revert_url_name: Incomplete
    revisions_compare_url_name: Incomplete
    revisions_unschedule_url_name: Incomplete
    @cached_property
    def columns(self): ...
    def get_base_object_queryset(self): ...
    def get_page_subtitle(self): ...
    def get_breadcrumbs_items(self): ...
    @cached_property
    def header_buttons(self): ...
    def get_edit_url(self, instance): ...
    def get_history_url(self, instance): ...
    def get_history_results_url(self, instance): ...
    def get_index_url(self): ...
    def get_index_results_url(self): ...
    def user_can_unschedule(self): ...
    def get_context_data(self, *args, object_list: Incomplete | None = None, **kwargs): ...
    def get_base_queryset(self): ...
    def get_filterset_kwargs(self): ...

class WorkflowHistoryView(BaseObjectMixin, WagtailAdminTemplateMixin, TemplateView):
    template_name: str
    page_kwarg: str
    workflow_history_url_name: Incomplete
    workflow_history_detail_url_name: Incomplete
    @cached_property
    def workflow_states(self): ...
    def get_context_data(self, **kwargs): ...

class WorkflowHistoryDetailView(BaseObjectMixin, WagtailAdminTemplateMixin, TemplateView):
    template_name: str
    workflow_state_url_kwarg: str
    workflow_history_url_name: Incomplete
    page_title: ClassVar[StrOrPromise]
    header_icon: ClassVar[str]
    object_icon: str
    @cached_property
    def workflow_state(self): ...
    @cached_property
    def revisions(self): ...
    @cached_property
    def tasks(self): ...
    @cached_property
    def task_states_by_revision(self): ...
    @cached_property
    def timeline(self): ...
    def get_context_data(self, **kwargs): ...
