# pyright: basic, reportGeneralTypeIssues=false
from typing import Any, Callable, ClassVar, Dict, Generic, List, Optional, Type, TypeVar, Union

from django.db import models
from django.db.models import Model, QuerySet
from django.forms import BaseModelForm, ModelForm
from django.http import HttpRequest, HttpResponse
from django.urls import URLPattern
from wagtail.admin.forms import WagtailAdminModelForm
from wagtail.admin.panels import ObjectList
from wagtail.admin.ui.tables import Column
from wagtail.admin.views import generic
from wagtail.admin.views.generic.history import HistoryView
from wagtail.admin.views.generic.usage import UsageView
from wagtail.admin.viewsets.base import ViewSet, ViewSetGroup
from wagtail.permissions import ModelPermissionPolicy

M = TypeVar('M', bound=Model)
QS = TypeVar('QS', bound=QuerySet, default=QuerySet[M])
ReqT = TypeVar('ReqT', bound=HttpRequest, default=HttpRequest)
MF = TypeVar('MF', bound=BaseModelForm, default=WagtailAdminModelForm)


class ModelViewSet(Generic[M, QS, ReqT, MF], ViewSet):
    add_to_reference_index: ClassVar[bool]
    index_view_class: ClassVar[type[generic.IndexView[M, QS]]]
    add_view_class: ClassVar[type[generic.CreateView[M, MF]]]
    edit_view_class: ClassVar[type[generic.EditView[M, MF]]]
    delete_view_class: ClassVar[type[generic.DeleteView[M]]]
    history_view_class: ClassVar[type[HistoryView]]
    usage_view_class: ClassVar[type[UsageView]]
    copy_view_class: ClassVar[type[generic.CopyView]]
    inspect_view_class: ClassVar[type[generic.InspectView]]
    _show_breadcrumbs: ClassVar[bool]
    template_prefix: ClassVar[str]
    list_per_page: ClassVar[int]
    ordering: ClassVar[str | list[str] | None]
    inspect_view_enabled: ClassVar[bool]
    inspect_view_fields: ClassVar[list[str]]
    inspect_view_fields_exclude: ClassVar[list[str]]
    copy_view_enabled: ClassVar[bool]
    model: type[M]
    model_opts: Any
    app_label: str
    model_name: str
    permission_policy: ClassVar[type[ModelPermissionPolicy]]

    def __init__(self, name: str | None = None, **kwargs: Any) -> None: ...
    def get_common_view_kwargs(self, **kwargs: Any) -> dict[str, Any]: ...
    def get_index_view_kwargs(self, **kwargs: Any) -> dict[str, Any]: ...
    def get_add_view_kwargs(self, **kwargs: Any) -> dict[str, Any]: ...
    def get_edit_view_kwargs(self, **kwargs: Any) -> dict[str, Any]: ...
    def get_delete_view_kwargs(self, **kwargs: Any) -> dict[str, Any]: ...
    def get_history_view_kwargs(self, **kwargs: Any) -> dict[str, Any]: ...
    def get_usage_view_kwargs(self, **kwargs: Any) -> dict[str, Any]: ...
    def get_inspect_view_kwargs(self, **kwargs: Any) -> dict[str, Any]: ...
    def get_copy_view_kwargs(self, **kwargs: Any) -> dict[str, Any]: ...
    @property
    def index_view(self) -> generic.IndexView: ...
    @property
    def index_results_view(self) -> generic.IndexView: ...
    @property
    def add_view(self) -> generic.CreateView: ...
    @property
    def edit_view(self) -> generic.EditView: ...
    @property
    def delete_view(self) -> generic.DeleteView: ...
    @property
    def redirect_to_edit_view(self) -> Callable[[HttpRequest, str], HttpResponse]: ...
    @property
    def redirect_to_delete_view(self) -> Callable[[HttpRequest, str], HttpResponse]: ...
    @property
    def history_view(self) -> HistoryView: ...
    @property
    def history_results_view(self) -> HistoryView: ...
    @property
    def usage_view(self) -> UsageView: ...
    @property
    def inspect_view(self) -> generic.InspectView: ...
    @property
    def copy_view(self) -> generic.CopyView: ...
    def get_templates(self, name: str = "index", fallback: str = "") -> list[str]: ...
    index_template_name: ClassVar[str | list[str]]
    index_results_template_name: ClassVar[str | list[str]]
    create_template_name: ClassVar[str | list[str]]
    edit_template_name: ClassVar[str | list[str]]
    delete_template_name: ClassVar[str | list[str]]
    history_template_name: ClassVar[str | list[str]]
    inspect_template_name: ClassVar[str | list[str]]
    list_display: ClassVar[list[str | Column]]
    list_filter: ClassVar[list[str] | dict[str, list[str]]]
    filterset_class: ClassVar[Any]
    search_fields: ClassVar[list[str] | None]
    search_backend_name: ClassVar[str | None]
    list_export: ClassVar[list[str]]
    export_headings: ClassVar[dict[str, str]]
    export_filename: ClassVar[str]
    menu_label: ClassVar[str]
    menu_item_class: ClassVar[Any]
    def formfield_for_dbfield(self, db_field: models.Field, **kwargs: Any) -> Any: ...
    def get_form_class(self, for_update: bool = False) -> type[ModelForm]: ...
    def get_form_fields(self) -> list[str] | None: ...
    def get_exclude_form_fields(self) -> list[str] | None: ...
    def get_edit_handler(self) -> ObjectList | None: ...
    _edit_handler: ClassVar[ObjectList | None]
    @property
    def url_finder_class(self) -> Any: ...
    def register_admin_url_finder(self) -> None: ...
    def register_reference_index(self) -> None: ...
    def get_urlpatterns(self) -> list[URLPattern]: ...
    _legacy_urlpatterns: ClassVar[list[URLPattern]]
    def on_register(self) -> None: ...

class ModelViewSetGroup(ViewSetGroup):
    def get_app_label_from_subitems(self) -> str: ...
    menu_label: ClassVar[str]
