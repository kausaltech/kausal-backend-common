from functools import cached_property
from typing import Any, ClassVar, Generic, Sequence
from typing_extensions import TypeVar

from django.db.models import Model, QuerySet
from django.forms import BaseModelForm
from django.http import HttpRequest, HttpResponse
from django.http.response import HttpResponseBase
from django.utils.safestring import SafeString
from wagtail.admin.forms.models import WagtailAdminModelForm
from wagtail.admin.panels import Panel
from wagtail.admin.ui.editing_sessions import EditingSessionsModule
from wagtail.admin.ui.tables import Column
from wagtail.admin.views.generic.models import LastUpdatedInfo
from wagtail.locks import BasicLock, ScheduledForPublishLock, WorkflowLock
from wagtail.models import Locale, Task, Workflow, WorkflowState

_ModelT = TypeVar('_ModelT', bound=Model, default=Model, covariant=True)
_FormT = TypeVar('_FormT', bound=BaseModelForm, default=WagtailAdminModelForm[Any], covariant=True)

class HookResponseMixin:
    def run_hook(self, hook_name: str, *args: Any, **kwargs: Any) -> HttpResponse | None: ...

class BeforeAfterHookMixin(Generic[_FormT], HookResponseMixin):
    def run_before_hook(self) -> HttpResponse | None: ...
    def run_after_hook(self) -> HttpResponse | None: ...
    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponseBase: ...
    def form_valid(self, form: _FormT) -> HttpResponse: ...  # type: ignore[misc]


type LocaleTranslationURL = dict[Locale, str]

class LocaleMixin:
    locale: ClassVar[Locale | None]
    translations: ClassVar[list[dict[str, Any]]]
    def get_locale(self) -> Locale | None: ...
    def get_translations(self) -> list[LocaleTranslationURL]: ...
    def get_context_data(self, **kwargs: Any) -> dict[str, Any]: ...

class PanelMixin(Generic[_FormT]):
    panel: ClassVar[Panel | None]
    def get_panel(self) -> Panel | None: ...
    def get_bound_panel(self, form: _FormT) -> Panel.BoundPanel | None: ...  # type: ignore[misc]
    def get_form_class(self) -> type[_FormT]: ...
    def get_context_data(self, **kwargs: Any) -> dict[str, Any]: ...

class IndexViewOptionalFeaturesMixin[QS: QuerySet]:
    def _get_title_column(self, field_name: str, column_class: type[Column] = ..., **kwargs: Any) -> Column: ...
    def _annotate_queryset_updated_at(self, queryset: QS) -> QS: ...


class CreateEditViewOptionalFeaturesMixin(Generic[_ModelT, _FormT]):
    view_name: ClassVar[str]
    preview_url_name: ClassVar[str | None]
    lock_url_name: ClassVar[str | None]
    unlock_url_name: ClassVar[str | None]
    revisions_unschedule_url_name: ClassVar[str | None]
    revisions_compare_url_name: ClassVar[str | None]
    workflow_history_url_name: ClassVar[str | None]
    confirm_workflow_cancellation_url_name: ClassVar[str | None]

    args: tuple[Any, ...]
    kwargs: dict[str, Any]
    preview_enabled: bool
    revision_enabled: bool
    draftstate_enabled: bool
    locking_enabled: bool
    lock: BasicLock | ScheduledForPublishLock | WorkflowLock | None
    locked_for_user: bool

    @cached_property
    def workflow(self) -> Workflow | None: ...

    @cached_property
    def workflow_enabled(self) -> bool: ...
    @cached_property
    def workflow_state(self) -> WorkflowState | None: ...
    @cached_property
    def current_workflow_task(self) -> Task | None: ...
    @cached_property
    def workflow_tasks(self) -> Sequence[Task]: ...

    def workflow_action_is_valid(self) -> bool: ...
    def get_available_actions(self) -> list[str]: ...
    def get_lock(self) -> BasicLock | ScheduledForPublishLock | WorkflowLock | None: ...
    def get_lock_url(self) -> str | None: ...
    def get_unlock_url(self) -> str | None: ...
    def get_preview_url(self) -> str | None: ...
    def get_workflow_history_url(self) -> str | None: ...
    def get_confirm_workflow_cancellation_url(self) -> str | None: ...
    def get_error_message(self) -> str: ...
    def get_success_message(self, instance: _ModelT | None = None) -> str: ...
    def get_success_url(self) -> str: ...
    def save_instance(self) -> _ModelT: ...
    def publish_action(self) -> HttpResponse | None: ...
    def submit_action(self) -> None: ...
    def restart_workflow_action(self) -> None: ...
    def cancel_workflow_action(self) -> None: ...
    def workflow_action_action(self) -> None: ...
    def run_action_method(self) -> HttpResponse | None: ...
    def form_valid(self, form: _FormT) -> HttpResponse: ...  # type: ignore[misc]
    def form_invalid(self, form: _FormT) -> HttpResponse: ...  # type: ignore[misc]
    def get_last_updated_info(self) -> LastUpdatedInfo | None: ...
    def get_lock_context(self) -> dict[str, Any]: ...
    def get_editing_sessions(self) -> EditingSessionsModule | None: ...

class RevisionsRevertMixin(Generic[_ModelT]):
    revision_id_kwarg: ClassVar[str]
    revisions_revert_url_name: ClassVar[str | None]
    revision_id: str
    revision: Any

    def get_revisions_revert_url(self) -> str: ...
    def get_warning_message(self) -> SafeString: ...
    def _add_warning_message(self) -> None: ...
    def get_object(self, queryset: QuerySet | None = None) -> _ModelT: ...
    def save_instance(self) -> _ModelT: ...
    def get_success_message(self) -> str: ...
