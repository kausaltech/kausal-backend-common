from typing import Any, ClassVar, Dict, Generic, List, Optional, Type, TypeVar
from django.db.models import Model, QuerySet
from django.forms import BaseModelForm
from django.http import HttpRequest, HttpResponse
from wagtail.admin.ui.tables import Column
from wagtail.admin.views import generic
from wagtail.admin.views.generic import models as generic_models
from wagtail.admin.views.generic import history, preview, base, mixins, lock, workflow

from wagtail.admin.viewsets.model import ModelViewSet
from wagtail.admin.panels import ObjectList
from wagtail.snippets.views.chooser import SnippetChooserViewSet

M = TypeVar('M', bound=Model)
QS = TypeVar('QS', bound=QuerySet)
ReqT = TypeVar('ReqT', bound=HttpRequest)

def get_snippet_model_from_url_params(app_name: str, model_name: str) -> Type[Model]: ...

class ModelIndexView(base.BaseListingView[M, QS, ReqT]):
    page_title: ClassVar[str]
    header_icon: ClassVar[str]
    index_url_name: ClassVar[str]
    default_ordering: ClassVar[str]
    snippet_types: List[Dict[str, Any]]
    columns: List[Column]
    def get_breadcrumbs_items(self) -> List[Dict[str, str]]: ...
    def get_list_url(self, type: Dict[str, Any]) -> str: ...
    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]: ...
    def get_template_names(self) -> List[str]: ...


class IndexView[M: Model, QS: QuerySet](mixins.IndexViewOptionalFeaturesMixin[QS], generic_models.IndexView[M, QS]):
    view_name: ClassVar[str]
    def get_base_queryset(self) -> QS: ...
    def get_list_buttons(self, instance: M) -> List[Any]: ...

class CreateView[M: Model, QS: QuerySet, F: BaseModelForm](mixins.CreateEditViewOptionalFeaturesMixin[M, QS, F], generic_models.CreateView[M, F]):
    view_name: ClassVar[str]
    def run_before_hook(self) -> Optional[HttpResponse]: ...
    def run_after_hook(self) -> Optional[HttpResponse]: ...
    def get_side_panels(self) -> Any: ...
    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]: ...

class CopyView[M: Model, QS: QuerySet, F: BaseModelForm](generic.CopyViewMixin[M], CreateView[M, QS, F]): ...

class EditView[M: Model, QS: QuerySet, F: BaseModelForm](generic.CreateEditViewOptionalFeaturesMixin[M, QS, F], generic.EditView[M, F]):
    view_name: ClassVar[str]
    def run_before_hook(self) -> Optional[HttpResponse]: ...
    def run_after_hook(self) -> Optional[HttpResponse]: ...
    def get_side_panels(self) -> Any: ...
    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]: ...


class DeleteView(generic.DeleteView):
    view_name: ClassVar[str]
    def run_before_hook(self) -> Optional[HttpResponse]: ...
    def run_after_hook(self) -> Optional[HttpResponse]: ...

class UsageView(generic.UsageView):
    view_name: ClassVar[str]

class HistoryView(history.HistoryView):
    view_name: ClassVar[str]

class InspectView(generic.InspectView):
    view_name: ClassVar[str]

class PreviewOnCreateView(preview.PreviewOnCreate): ...
class PreviewOnEditView(preview.PreviewOnEdit): ...

class PreviewRevisionView(generic.PermissionCheckedMixin, preview.PreviewRevision):
    pass


class RevisionsCompareView(generic.PermissionCheckedMixin, generic.RevisionsCompareView):
    pass

class UnpublishView(generic.PermissionCheckedMixin, generic.UnpublishView):
    pass

class RevisionsUnscheduleView(generic.PermissionCheckedMixin, generic.RevisionsUnscheduleView):
    pass

class LockView(generic.PermissionCheckedMixin, lock.LockView):
    def user_has_permission(self, permission: str) -> bool: ...

class UnlockView(generic.PermissionCheckedMixin, lock.UnlockView):
    def user_has_permission(self, permission: str) -> bool: ...

class WorkflowActionView(workflow.WorkflowAction): ...
class CollectWorkflowActionDataView(workflow.CollectWorkflowActionData): ...
class ConfirmWorkflowCancellationView(workflow.ConfirmWorkflowCancellation): ...
class WorkflowPreviewView(workflow.PreviewRevisionForTask): ...

class WorkflowHistoryView(generic.PermissionCheckedMixin, history.WorkflowHistoryView):
    pass

class WorkflowHistoryDetailView(generic.PermissionCheckedMixin, history.WorkflowHistoryDetailView):
    pass


class SnippetViewSet(ModelViewSet[M, QS, ReqT]):
    model: Type[M]
    chooser_per_page: ClassVar[int]
    admin_url_namespace: ClassVar[Optional[str]]
    base_url_path: ClassVar[Optional[str]]
    chooser_admin_url_namespace: ClassVar[Optional[str]]
    chooser_base_url_path: ClassVar[Optional[str]]
    index_view_class: ClassVar[Type[IndexView]]
    add_view_class: ClassVar[Type[CreateView]]
    copy_view_class: ClassVar[Type[CopyView]]  # type: ignore
    edit_view_class: ClassVar[Type[EditView]]
    delete_view_class: ClassVar[Type[DeleteView]]
    usage_view_class: ClassVar[Type[UsageView]]
    history_view_class: ClassVar[Type[HistoryView]]
    inspect_view_class: ClassVar[Type[InspectView]]
    revisions_view_class: ClassVar[Type[PreviewRevisionView]]
    revisions_compare_view_class: ClassVar[Type[RevisionsCompareView]]
    revisions_unschedule_view_class: ClassVar[Type[RevisionsUnscheduleView]]
    unpublish_view_class: ClassVar[Type[UnpublishView]]
    preview_on_add_view_class: ClassVar[Type[PreviewOnCreateView]]
    preview_on_edit_view_class: ClassVar[Type[PreviewOnEditView]]
    lock_view_class: ClassVar[Type[LockView]]
    unlock_view_class: ClassVar[Type[UnlockView]]
    workflow_action_view_class: ClassVar[Type[WorkflowActionView]]
    collect_workflow_action_data_view_class: ClassVar[Type[CollectWorkflowActionDataView]]
    confirm_workflow_cancellation_view_class: ClassVar[Type[ConfirmWorkflowCancellationView]]
    workflow_preview_view_class: ClassVar[Type[WorkflowPreviewView]]
    workflow_history_view_class: ClassVar[Type[WorkflowHistoryView]]
    workflow_history_detail_view_class: ClassVar[Type[WorkflowHistoryDetailView]]
    chooser_viewset_class: ClassVar[Type[SnippetChooserViewSet]]
    template_prefix: ClassVar[str]
    model_opts: Any
    app_label: str
    model_name: str
    preview_enabled: bool
    revision_enabled: bool
    draftstate_enabled: bool
    workflow_enabled: bool
    locking_enabled: bool
    menu_item_is_registered: bool

    def __init__(self, **kwargs: Any) -> None: ...
    @property
    def revisions_revert_view_class(self) -> Type[Any]: ...
    def get_common_view_kwargs(self, **kwargs: Any) -> Dict[str, Any]: ...
    def get_index_view_kwargs(self, **kwargs: Any) -> Dict[str, Any]: ...
    def get_add_view_kwargs(self, **kwargs: Any) -> Dict[str, Any]: ...
    def get_copy_view_kwargs(self, **kwargs: Any) -> Dict[str, Any]: ...
    def get_edit_view_kwargs(self, **kwargs: Any) -> Dict[str, Any]: ...
    @property
    def revisions_view(self) -> Any: ...
    @property
    def revisions_revert_view(self) -> Any: ...
    @property
    def revisions_compare_view(self) -> Any: ...
    @property
    def revisions_unschedule_view(self) -> Any: ...
    @property
    def unpublish_view(self) -> Any: ...
    @property
    def preview_on_add_view(self) -> Any: ...
    @property
    def preview_on_edit_view(self) -> Any: ...
    @property
    def lock_view(self) -> Any: ...
    @property
    def copy_view(self) -> Any: ...
    @property
    def unlock_view(self) -> Any: ...
    @property
    def workflow_action_view(self) -> Any: ...
    @property
    def collect_workflow_action_data_view(self) -> Any: ...
    @property
    def confirm_workflow_cancellation_view(self) -> Any: ...
    @property
    def workflow_preview_view(self) -> Any: ...
    @property
    def workflow_history_view(self) -> Any: ...
    @property
    def workflow_history_detail_view(self) -> Any: ...
    @property
    def redirect_to_usage_view(self) -> Any: ...
    @property
    def chooser_viewset(self) -> Any: ...
    list_display: ClassVar[List[str]]
    icon: ClassVar[str]
    menu_label: ClassVar[str]
    menu_name: ClassVar[str]
    menu_icon: ClassVar[str]
    menu_order: ClassVar[int]
    breadcrumbs_items: ClassVar[List[Dict[str, str]]]
    def get_queryset(self, request: ReqT) -> Optional[QS]: ...
    index_template_name: ClassVar[str]
    index_results_template_name: ClassVar[str]
    create_template_name: ClassVar[str]
    edit_template_name: ClassVar[str]
    delete_template_name: ClassVar[str]
    history_template_name: ClassVar[str]
    inspect_template_name: ClassVar[str]
    def get_admin_url_namespace(self) -> str: ...
    def get_admin_base_path(self) -> str: ...
    def get_chooser_admin_url_namespace(self) -> str: ...
    def get_chooser_admin_base_path(self) -> str: ...
    @property
    def url_finder_class(self) -> Type[Any]: ...
    def get_urlpatterns(self) -> List[Any]: ...
    def get_edit_handler(self) -> ObjectList: ...
    def register_chooser_viewset(self) -> None: ...
    def register_model_check(self) -> None: ...
    def register_snippet_model(self) -> None: ...
    def on_register(self) -> None: ...

class SnippetViewSetGroup(ModelViewSet):
    def __init__(self) -> None: ...
