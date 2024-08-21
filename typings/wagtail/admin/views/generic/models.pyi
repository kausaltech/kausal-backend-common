from typing import Any, ClassVar, Generic
from typing_extensions import TypeVar

from django.db.models import Model, QuerySet
from django.forms import BaseModelForm
from django.http import HttpRequest, HttpResponse
from django.utils.functional import cached_property
from django.views.generic import TemplateView
from django.views.generic.edit import BaseCreateView, BaseDeleteView, BaseUpdateView
from wagtail.admin.filters import WagtailFilterSet
from wagtail.admin.forms import WagtailAdminModelForm
from wagtail.admin.forms.search import SearchForm
from wagtail.admin.panels import Panel
from wagtail.admin.ui.components import Component
from wagtail.admin.ui.tables import Column
from wagtail.admin.views.mixins import SpreadsheetExportMixin
from wagtail.admin.widgets.button import ButtonWithDropdown, HeaderButton, ListingButton
from wagtail.models import DraftStateMixin, Locale, ReferenceIndex
from wagtail.models.audit_log import ModelLogEntry

from .base import BaseListingView, WagtailAdminTemplateMixin
from .mixins import BeforeAfterHookMixin, HookResponseMixin, LocaleMixin, PanelMixin
from .permissions import PermissionCheckedMixin

_Model = TypeVar('_Model', bound=Model, default=Model)
_QS = TypeVar('_QS', bound=QuerySet, default=QuerySet[_Model])
_Form = TypeVar('_Form', bound=BaseModelForm, default=WagtailAdminModelForm)


class IndexView(Generic[_Model], SpreadsheetExportMixin, LocaleMixin, PermissionCheckedMixin, BaseListingView[_Model]):
    model: type[_Model] | None
    add_url_name: ClassVar[str | None]
    edit_url_name: ClassVar[str | None]
    copy_url_name: ClassVar[str | None]
    inspect_url_name: ClassVar[str | None]
    delete_url_name: ClassVar[str | None]
    search_fields: ClassVar[list[str] | None]
    search_backend_name: ClassVar[str]
    is_searchable: ClassVar[bool | None]
    search_kwarg: ClassVar[str]
    list_display: ClassVar[list[str | Column]]
    list_filter: ClassVar[list[str] | None]
    show_other_searches: ClassVar[bool]
    add_url: ClassVar[str | None]

    search_url: str
    search_form: SearchForm | None
    is_searching: bool
    search_query: str | None
    header_buttons: ClassVar[list[HeaderButton]]
    add_item_label: ClassVar[str]

    def setup_search(self) -> None: ...
    def get_is_searchable(self) -> bool: ...
    def get_search_url(self) -> str | None: ...
    def get_search_form(self) -> SearchForm | None: ...
    def get_filterset_class(self) -> type[WagtailFilterSet] | None: ...
    def search_queryset[QS: QuerySet](self, queryset: QS) -> QS: ...
    def get_edit_url(self, instance: _Model) -> str | None: ...
    def get_copy_url(self, instance: _Model) -> str | None: ...
    def get_inspect_url(self, instance: _Model) -> str | None: ...
    def get_delete_url(self, instance: _Model) -> str | None: ...
    def get_add_url(self) -> str | None: ...
    def get_list_more_buttons(self, instance: _Model) -> list[ListingButton]: ...
    def get_list_buttons(self, instance: _Model) -> list[ButtonWithDropdown]: ...
    def get_context_data(self, *args: Any, **kwargs: Any) -> dict[str, Any]: ...
    def render_to_response(self, context: dict[str, Any], **response_kwargs: Any) -> HttpResponse: ...

type SuccessButton = tuple[str, str, bool]

class CreateView(
    Generic[_Model, _Form],
    LocaleMixin,
    PanelMixin[_Form],
    PermissionCheckedMixin,
    BeforeAfterHookMixin[_Form],
    WagtailAdminTemplateMixin,
    BaseCreateView[_Model, _Form],
):  # pyright: ignore
    index_url_name: ClassVar[str | None]
    add_url_name: ClassVar[str | None]
    edit_url_name: ClassVar[str | None]
    success_message: ClassVar[str | None]
    error_message: ClassVar[str | None]
    submit_button_label: ClassVar[str]
    actions: ClassVar[list[str]]

    action: str
    form: _Form

    def get_action(self, request: HttpRequest) -> str: ...
    def get_available_actions(self) -> list[str]: ...
    def get_add_url(self) -> str: ...
    @cached_property
    def add_url(self) -> str: ...
    def get_edit_url(self) -> str: ...
    def get_success_url(self) -> str: ...
    def get_success_message(self, instance: _Model) -> str | None: ...
    def get_success_buttons(self) -> list[SuccessButton]: ...
    def get_error_message(self) -> str | None: ...
    def get_side_panels(self) -> Component: ...
    def get_translations(self) -> list[dict[str, Any]]: ...
    def get_initial_form_instance(self) -> _Model | None: ...
    def get_form_kwargs(self) -> dict[str, Any]: ...
    def save_instance(self) -> _Model: ...
    def save_action(self) -> HttpResponse: ...
    def form_valid(self, form: _Form) -> HttpResponse: ...
    def form_invalid(self, form: _Form) -> HttpResponse: ...

class CopyViewMixin(Generic[_Model]):
    def get_object(self, queryset: QuerySet | None = None) -> _Model: ...
    def get_initial_form_instance(self) -> _Model: ...

class CopyView(CopyViewMixin[_Model], CreateView[_Model, _Form]): ...

class EditView(
    Generic[_Model, _Form], LocaleMixin, PanelMixin[_Form], PermissionCheckedMixin, BeforeAfterHookMixin[_Form],
    WagtailAdminTemplateMixin, BaseUpdateView,
):
    index_url_name: ClassVar[str | None]
    edit_url_name: ClassVar[str | None]
    delete_url_name: ClassVar[str | None]
    history_url_name: ClassVar[str | None]
    usage_url_name: ClassVar[str | None]
    delete_item_label: ClassVar[str]
    success_message: ClassVar[str | None]
    error_message: ClassVar[str | None]
    submit_button_label: ClassVar[str]
    actions: ClassVar[list[str]]

    action: str
    form: _Form
    has_content_changes: bool

    request: HttpRequest

    def get_action(self, request: HttpRequest) -> str: ...
    def get_available_actions(self) -> list[str]: ...
    def get_object(self, queryset: QuerySet | None = None) -> _Model: ...
    def get_page_subtitle(self) -> str: ...
    def get_side_panels(self) -> Component: ...
    def get_last_updated_info(self) -> ModelLogEntry | None: ...
    def get_edit_url(self) -> str: ...
    def get_delete_url(self) -> str | None: ...
    def get_history_url(self) -> str | None: ...
    def get_usage_url(self) -> str | None: ...
    def get_success_url(self) -> str: ...
    def get_translations(self) -> list[dict[str, Locale]]: ...
    def get_form_kwargs(self) -> dict[str, Any]: ...
    def save_instance(self) -> _Model: ...
    def save_action(self) -> HttpResponse: ...
    def get_success_message(self) -> str | None: ...
    def get_success_buttons(self) -> list[SuccessButton]: ...
    def get_error_message(self) -> str | None: ...
    def get_context_data(self, **kwargs: Any) -> dict[str, Any]: ...


class DeleteView(
    Generic[_Model, _Form],
    LocaleMixin,
    PanelMixin[_Form],
    PermissionCheckedMixin,
    BeforeAfterHookMixin[_Form],
    WagtailAdminTemplateMixin,
    BaseDeleteView[_Model, _Form],
):
    index_url_name: ClassVar[str | None]
    edit_url_name: ClassVar[str | None]
    delete_url_name: ClassVar[str | None]
    usage_url_name: ClassVar[str | None]
    page_title: ClassVar[str]
    success_message: ClassVar[str | None]

    object: _Model
    usage_url: str | None
    usage: ReferenceIndex | None

    def setup(self, request: HttpRequest, *args: Any, **kwargs: Any) -> None: ...
    def get_object(self, queryset: QuerySet | None = None) -> _Model: ...
    def get_usage(self) -> ReferenceIndex | None: ...
    def get_success_url(self) -> str: ...
    def get_page_subtitle(self) -> str: ...
    def get_delete_url(self) -> str: ...
    def get_usage_url(self) -> str | None: ...
    @property
    def confirmation_message(self) -> str: ...
    def get_success_message(self) -> str | None: ...
    def delete_action(self) -> None: ...
    def form_valid(self, form: _Form) -> HttpResponse: ...
    def get_context_data(self, **kwargs: Any) -> dict[str, Any]: ...

class InspectView[M: Model](PermissionCheckedMixin, WagtailAdminTemplateMixin, TemplateView):
    model: type[M] | None
    index_url_name: ClassVar[str | None]
    edit_url_name: ClassVar[str | None]
    delete_url_name: ClassVar[str | None]
    fields: ClassVar[list[str]]
    fields_exclude: ClassVar[list[str]]
    pk_url_kwarg: ClassVar[str]

    pk: Any
    object: M

    def setup(self, request: HttpRequest, *args: Any, **kwargs: Any) -> None: ...
    def get_object(self, queryset: QuerySet | None = None) -> M: ...
    def get_page_subtitle(self) -> str: ...
    def get_fields(self) -> list[str]: ...
    def get_field_label(self, field_name: str, field: Any) -> str: ...
    def get_field_display_value(self, field_name: str, field: Any) -> Any: ...
    def get_context_for_field(self, field_name: str) -> dict[str, Any]: ...
    def get_fields_context(self) -> list[dict[str, Any]]: ...
    def get_edit_url(self) -> str | None: ...
    def get_delete_url(self) -> str | None: ...
    def get_context_data(self, **kwargs: Any) -> dict[str, Any]: ...


class RevisionsCompareView(Generic[_Model], WagtailAdminTemplateMixin, TemplateView):
    edit_handler: ClassVar[Panel | None]
    edit_url_name: ClassVar[str | None]
    history_url_name: ClassVar[str | None]
    edit_label: ClassVar[str]
    history_label: ClassVar[str]
    model: type[_Model]

    pk: Any
    revision_id_a: str
    revision_id_b: str
    object: _Model

    def setup(self, request: HttpRequest, pk: Any, revision_id_a: str, revision_id_b: str, *args: Any, **kwargs: Any) -> None: ...
    def get_object(self, queryset: QuerySet | None = None) -> _Model: ...
    def get_edit_handler(self) -> Panel: ...
    def get_page_subtitle(self) -> str: ...
    def get_history_url(self) -> str | None: ...
    def get_edit_url(self) -> str | None: ...
    def get_context_data(self, **kwargs: Any) -> dict[str, Any]: ...


class UnpublishView[M: Model](HookResponseMixin, WagtailAdminTemplateMixin, TemplateView):
    model: type[M] | None
    index_url_name: ClassVar[str | None]
    edit_url_name: ClassVar[str | None]
    unpublish_url_name: ClassVar[str | None]
    usage_url_name: ClassVar[str | None]
    success_message: ClassVar[str | None]

    pk: Any
    object: M
    objects_to_unpublish: list[M]

    def setup(self, request: HttpRequest, pk: Any, *args: Any, **kwargs: Any) -> None: ...
    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse: ...
    def get_object(self, queryset: QuerySet[M] | None = None) -> M: ...
    def get_usage(self) -> ReferenceIndex: ...
    def get_objects_to_unpublish(self) -> list[M]: ...
    def get_object_display_title(self) -> str: ...
    def get_success_message(self) -> str | None: ...
    def get_success_buttons(self) -> list[Any]: ...
    def get_next_url(self) -> str: ...
    def get_unpublish_url(self) -> str: ...
    def get_usage_url(self) -> str | None: ...
    def unpublish(self) -> HttpResponse | None: ...
    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse: ...
    def get_context_data(self, **kwargs: Any) -> dict[str, Any]: ...


class RevisionsUnscheduleView[M: DraftStateMixin](WagtailAdminTemplateMixin, TemplateView):
    model: type[M] | None
    edit_url_name: ClassVar[str | None]
    history_url_name: ClassVar[str | None]
    revisions_unschedule_url_name: ClassVar[str | None]
    success_message: ClassVar[str | None]

    pk: Any
    revision_id: str
    object: M
    revision: Any

    def setup(self, request: HttpRequest, pk: Any, revision_id: str, *args: Any, **kwargs: Any) -> None: ...
    def get_object(self, queryset: QuerySet[M] | None = None) -> M: ...
    def get_revision(self) -> Any: ...
    def get_revisions_unschedule_url(self) -> str: ...
    def get_object_display_title(self) -> str: ...
    def get_success_message(self) -> str | None: ...
    def get_success_buttons(self) -> list[SuccessButton]: ...
    def get_next_url(self) -> str: ...
    def get_page_subtitle(self) -> str: ...
    def get_context_data(self, **kwargs: Any) -> dict[str, Any]: ...
    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse: ...
