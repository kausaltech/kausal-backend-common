from typing import Any, ClassVar

from django.contrib.auth.decorators import login_required
from django.db.models import Model
from django.forms import BaseForm, ModelForm
from django.http.request import HttpRequest
from django.utils.decorators import method_decorator
from django.utils.functional import cached_property
from django.views.generic import TemplateView
from django.views.generic.edit import FormView
from django.views.generic.list import MultipleObjectMixin
from django_stubs_ext import StrOrPromise
from wagtail.admin.views.generic.base import WagtailAdminTemplateMixin
from wagtail.admin.views.mixins import SpreadsheetExportMixin

from wagtail_modeladmin.helpers import AdminURLHelper, PermissionHelper
from wagtail_modeladmin.options import ModelAdmin

QUERY_TERMS = ...
class WMABaseView[M: Model](TemplateView):
    """
    Groups together common functionality for all app views.
    """
    verbose_name: str
    verbose_name_plural: str
    url_helper: AdminURLHelper
    model: type[M]
    model_admin: ModelAdmin[M]
    model_name: str
    meta_title: StrOrPromise | None
    page_title: ClassVar[StrOrPromise]
    page_subtitle: ClassVar[StrOrPromise]
    permission_helper: PermissionHelper[M]

    def __init__(self, model_admin: ModelAdmin[M]) -> None:
        ...

    def check_action_permitted(self, user): # -> Literal[True]:
        ...

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs): # -> HttpResponseBase:
        ...

    @cached_property
    def menu_icon(self):
        ...

    @cached_property
    def header_icon(self):
        ...

    def get_page_title(self): # -> str:
        ...

    def get_meta_title(self): # -> str:
        ...

    @cached_property
    def index_url(self):
        ...

    @cached_property
    def create_url(self):
        ...

    def get_base_queryset(self, request=...):
        ...

    def get_context_data(self, **kwargs: Any): # -> dict[str, Any]:
        ...



class ModelFormView[M: Model = Model, FormT: BaseForm = ModelForm[Any]](WMABaseView[M], FormView[FormT]):
    model_admin: ModelAdmin[M]

    def setup(self, request: HttpRequest, *args, **kwargs): # -> None:
        ...

    def get_form(self) -> FormT:  # type: ignore[override]
        ...

    def get_edit_handler(self):
        ...

    def get_form_class(self):
        ...

    def get_success_url(self):
        ...

    def get_instance(self): # -> Any:
        ...

    def get_form_kwargs(self): # -> dict[str, Any]:
        ...

    @property
    def media(self): # -> Media:
        ...

    def get_context_data(self, form: FormT | None = None, **kwargs: Any): # -> dict[str, Any]:
        ...

    def get_prepopulated_fields(self, form): # -> list[Any]:
        ...

    def get_success_message(self, instance): # -> str:
        ...

    def get_success_message_buttons(self, instance): # -> list[tuple[str, _StrOrPromise, bool]]:
        ...

    def get_error_message(self): # -> str:
        ...

    def form_valid(self, form): # -> HttpResponseRedirect:
        ...

    def form_invalid(self, form): # -> HttpResponse:
        ...



class InstanceSpecificView[M: Model](WMABaseView[M]):
    instance_pk: int
    pk_quoted: str
    instance: M
    locale = ...
    def __init__(self, model_admin, instance_pk) -> None:
        ...

    def get_page_subtitle(self): # -> None:
        ...

    @cached_property
    def edit_url(self):
        ...

    @cached_property
    def delete_url(self):
        ...

    # def get_context_data(self, **kwargs: Any): # -> dict[str, Any]:
    #     ...



class IndexView[M: Model](SpreadsheetExportMixin, WMABaseView[M]):
    ORDER_VAR = ...
    ORDER_TYPE_VAR = ...
    PAGE_VAR = ...
    SEARCH_VAR = ...
    ERROR_FLAG = ...
    EXPORT_VAR = ...
    IGNORED_PARAMS = ...
    sortable_by = ...
    add_facets = ...
    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs): # -> StreamingHttpResponse | FileResponse | HttpResponseBase | None:
        ...

    def get_filename(self): # -> Any | str:
        """Get filename for exported spreadsheet, without extension"""

    def get_heading(self, queryset, field):
        """Get headings for exported spreadsheet column for the relevant field"""

    def to_row_dict(self, item): # -> OrderedDict[Any, Any]:
        """Returns an OrderedDict (in the order given by list_export) of the exportable information for a model instance"""

    @property
    def media(self): # -> Media:
        ...

    def get_buttons_for_obj(self, obj):
        ...

    def get_search_results(self, request, queryset, search_term):
        ...

    def get_filters_params(self, params=...):
        """
        Returns all params except IGNORED_PARAMS
        """

    def get_filters(self, request): # -> tuple[list[Any], bool, Any, bool | Any]:
        ...

    def get_query_string(self, new_params=..., remove=...): # -> str:
        ...

    def get_default_ordering(self, request): # -> tuple[()]:
        ...

    def get_ordering_field(self, field_name): # -> Any | None:
        """
        Returns the proper model field name corresponding to the given
        field_name to use for ordering. field_name may either be the name of a
        proper model field or the name of a method (on the admin or model) or a
        callable with the 'admin_order_field' attribute. Returns None if no
        proper model field name can be matched.
        """

    def get_ordering(self, request, queryset): # -> list[Never]:
        """
        Returns the list of ordering fields for the change list.
        First we check the get_ordering() method in model admin, then we check
        the object's default ordering. Then, any manually-specified ordering
        from the query string overrides anything. Finally, a deterministic
        order is guaranteed by ensuring the primary key is used as the last
        ordering field.
        """

    def get_ordering_field_columns(self): # -> OrderedDict[Any, Any]:
        """
        Returns an OrderedDict of ordering field column numbers and asc/desc
        """

    def get_queryset(self, request=...):
        ...

    def apply_select_related(self, qs):
        ...

    def has_related_field_in_list_display(self): # -> bool:
        ...

    def get_context_data(self, **kwargs): # -> dict[str, Any]:
        ...

    def get_template_names(self):
        ...



class CreateView[M: Model, FormT: BaseForm = ModelForm[Any]](ModelFormView[M, FormT]):
    def check_action_permitted(self, user):
        ...

    def dispatch(self, request, *args, **kwargs): # -> HttpResponseRedirect | HttpResponseBase:
        ...

    def form_valid(self, form): # -> HttpResponseRedirect:
        ...

    def get_meta_title(self): # -> str:
        ...

    def get_page_subtitle(self):
        ...

    def get_template_names(self):
        ...

    def get_form_kwargs(self): # -> dict[str, Any]:
        ...



class EditView[M: Model, FormT: BaseForm = ModelForm[Any]](ModelFormView[M, FormT], InstanceSpecificView[M]):
    def check_action_permitted(self, user):
        ...

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs): # -> HttpResponseRedirect | HttpResponseBase:
        ...

    def get_meta_title(self): # -> str:
        ...

    def get_success_message(self, instance): # -> str:
        ...

    def get_error_message(self): # -> str:
        ...

    def get_template_names(self):
        ...

    def form_valid(self, form): # -> HttpResponseRedirect:
        ...



class ChooseParentView[M: Model](WMABaseView[M]):
    def dispatch(self, request, *args, **kwargs): # -> HttpResponseBase:
        ...

    def get_page_title(self): # -> str:
        ...

    def get_form(self, request): # -> ParentChooserForm:
        ...

    def get(self, request, *args, **kwargs): # -> HttpResponse:
        ...

    def post(self, request, *args, **kargs): # -> HttpResponseRedirect | HttpResponse:
        ...

    def form_valid(self, form): # -> HttpResponseRedirect:
        ...

    def form_invalid(self, form): # -> HttpResponse:
        ...

    def get_template_names(self):
        ...



class DeleteView[M: Model](InstanceSpecificView[M]):
    def check_action_permitted(self, user):
        ...

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs): # -> HttpResponseRedirect | HttpResponseBase:
        ...

    def get_meta_title(self): # -> str:
        ...

    def confirmation_message(self): # -> str:
        ...

    def delete_instance(self): # -> None:
        ...

    def post(self, request, *args, **kwargs): # -> HttpResponseRedirect | HttpResponse:
        ...

    def get_template_names(self):
        ...



class InspectView[M: Model](InstanceSpecificView[M]):
    def check_action_permitted(self, user):
        ...

    def dispatch(self, request, *args, **kwargs): # -> HttpResponseBase:
        ...

    @property
    def media(self): # -> Media:
        ...

    def get_meta_title(self): # -> str:
        ...

    def get_field_label(self, field_name, field=...): # -> tuple[str, Callable[..., Any] | str | None]:
        """Return a label to display for a field"""

    def get_field_display_value(self, field_name, field=...):
        # -> object | Any | str | SafeString | AbstractImage | AbstractDocument | Literal[False]:
        """Return a display value for a field/attribute"""

    def get_image_field_display(self, field_name, field): # -> Any:
        """Render an image"""

    def get_document_field_display(self, field_name, field): # -> SafeString:
        """Render a link to a document"""

    def get_dict_for_field(self, field_name):
        # -> dict[str, tuple[str, Callable[..., Any] | str | None] | object | Any | str
        # | SafeString | AbstractImage | AbstractDocument | bool]:
        """
        Return a dictionary containing `label` and `value` values to display
        for a field.
        """

    def get_fields_dict(self): # -> list[Any]:
        """
        Return a list of `label`/`value` dictionaries to represent the
        fields named by the model_admin class's `get_inspect_view_fields` method
        """

    def get_context_data(self, **kwargs): # -> dict[str, Any]:
        ...

    def get_template_names(self):
        ...



class HistoryView[M: Model](MultipleObjectMixin[M], WagtailAdminTemplateMixin, InstanceSpecificView[M]):
    model: type[M]
    def get_page_subtitle(self): # -> str:
        ...

    def get_template_names(self):
        ...

    def get_queryset(self): # -> QuerySet[BaseLogEntry, BaseLogEntry]:
        ...

    def get_context_data(self, **kwargs): # -> dict[str, Any]:
        ...



