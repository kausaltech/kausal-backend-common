from typing import Any, Sequence

from django.contrib.admin.filters import ListFilter
from django.contrib.admin.options import _ListDisplayT, _ListFilterT
from django.db.models import Model
from django.db.models.options import Options
from django.http.request import HttpRequest
from django_stubs_ext import StrOrPromise

from wagtail_modeladmin.helpers.button import ButtonHelper

from .helpers import (
    AdminURLHelper,
    DjangoORMSearchHandler,
    PageAdminURLHelper,
    PageButtonHelper,
    PagePermissionHelper,
    PermissionHelper,
)
from .views import ChooseParentView, CreateView, DeleteView, EditView, HistoryView, IndexView, InspectView

class WagtailRegisterable:
    """
    Base class, providing a more convenient way for ModelAdmin or
    ModelAdminGroup instances to be registered with Wagtail's admin area.
    """
    add_to_settings_menu: bool
    add_to_admin_menu: bool
    exclude_from_explorer: bool
    def register_with_wagtail(self): # -> None:
        ...

    def register_admin_url_finders(self): # -> None:
        ...

    def register_indexing(self): # -> None:
        ...

    def will_modify_explorer_page_queryset(self): # -> Literal[False]:
        ...



class ModelAdmin[M: Model](WagtailRegisterable):
    """
    The core modeladmin class. It provides an alternative means to
    list and manage instances of a given 'model' within Wagtail's admin area.
    It is essentially comprised of attributes and methods that allow a degree
    of control over how the data is represented, and other methods to make the
    additional functionality available via various Wagtail hooks.
    """
    model: type[M]
    opts: Options[M]
    menu_label: StrOrPromise | None
    menu_item_name: StrOrPromise | None
    menu_icon: str | None
    menu_order: int | None
    list_display: _ListDisplayT[M] | None
    list_display_add_buttons: str | None
    list_export = ...
    inspect_view_fields = ...
    inspect_view_fields_exclude = ...
    inspect_view_enabled: bool
    history_view_enabled: bool
    empty_value_display: str
    list_filter: _ListFilterT | Sequence[type[ListFilter]]
    list_select_related = ...
    list_per_page: int
    search_fields: Sequence[str] | None
    ordering: str | Sequence[str] | None
    parent = ...
    prepopulated_fields = ...
    index_view_class: type[IndexView[Any]]
    create_view_class: type[CreateView[Any, Any]]
    edit_view_class: type[EditView[Any, Any]]
    inspect_view_class: type[InspectView[Any]]
    delete_view_class: type[DeleteView[Any]]
    history_view_class: type[HistoryView[Any]]
    choose_parent_view_class: type[ChooseParentView[Any]]
    index_template_name: str
    create_template_name: str
    edit_template_name: str
    inspect_template_name: str
    delete_template_name: str | list[str]
    history_template_name: str
    choose_parent_template_name: str
    search_handler_class = DjangoORMSearchHandler
    extra_search_kwargs = ...
    permission_helper_class: type[PermissionHelper[Any]] = ...
    url_helper_class: type[AdminURLHelper] = ...
    button_helper_class: type[ButtonHelper] = ...
    index_view_extra_css: list[str]
    index_view_extra_js = ...
    inspect_view_extra_css = ...
    inspect_view_extra_js = ...
    form_view_extra_css = ...
    form_view_extra_js = ...
    form_fields_exclude = ...
    base_url_path = ...
    url_helper: AdminURLHelper
    permission_helper: PermissionHelper[M]

    def __init__(self, parent=...) -> None:
        """
        Don't allow initialisation unless self.model is set to a valid model
        """

    def get_permission_helper_class(self) -> type[PagePermissionHelper | PermissionHelper[M]]:
        """
        Returns a permission_helper class to help with permission-based logic
        for the given model.
        """

    def get_url_helper_class(self) -> type[PageAdminURLHelper | AdminURLHelper]: ...

    def get_button_helper_class(self) -> type[PageButtonHelper | ButtonHelper]:
        """
        Returns a ButtonHelper class to help generate buttons for the given
        model.
        """

    def get_menu_label(self) -> str:
        """
        Returns the label text to be used for the menu item.
        """

    def get_menu_item_name(self) -> str:
        """
        Returns the name to be used for the menu item.
        """

    def get_menu_icon(self) -> str:
        """
        Returns the icon to be used for the menu item. The value is prepended
        with 'icon-' to create the full icon class name. For design
        consistency, the same icon is also applied to the main heading for
        views called by this class.
        """

    def get_menu_order(self) -> int:
        """
        Returns the 'order' to be applied to the menu item. 000 being first
        place. Where ModelAdminGroup is used, the menu_order value should be
        applied to that, and any ModelAdmin classes added to 'items'
        attribute will be ordered automatically, based on their order in that
        sequence.
        """

    def get_list_display(self, request: HttpRequest): # -> tuple[Literal['__str__']]:
        """
        Return a sequence containing the fields/method output to be displayed
        in the list view.
        """

    def get_list_display_add_buttons(self, request: HttpRequest): # -> Literal['__str__']:
        """
        Return the name of the field/method from list_display where action
        buttons should be added. Defaults to the first item from
        get_list_display()
        """

    def get_list_export(self, request): # -> tuple[()]:
        """
        Return a sequence containing the fields/method output to be displayed
        in spreadsheet exports.
        """

    def get_empty_value_display(self, field_name=...): # -> SafeString:
        """
        Return the empty_value_display value defined on ModelAdmin
        """

    def get_list_filter(self, request): # -> tuple[Literal['locale']] | tuple[()]:
        """
        Returns a sequence containing the fields to be displayed as filters in
        the right sidebar in the list view.
        """

    def get_ordering(self, request): # -> tuple[()]:
        """
        Returns a sequence defining the default ordering for results in the
        list view.
        """

    def get_queryset(self, request):
        """
        Returns a QuerySet of all model instances that can be edited by the
        admin site.
        """

    def get_search_fields(self, request): # -> tuple[()]:
        """
        Returns a sequence defining which fields on a model should be searched
        when a search is initiated from the list view.
        """

    def get_search_handler(self, request, search_fields=...): # -> search_handler_class:
        """
        Returns an instance of ``self.search_handler_class`` that can be used by
        ``IndexView``.
        """

    def get_extra_search_kwargs(self, request, search_term): # -> dict[Any, Any]:
        """
        Returns a dictionary of additional kwargs to be sent to
        ``SearchHandler.search_queryset()``.
        """

    def get_extra_attrs_for_row(self, obj, context): # -> dict[Any, Any]:
        """
        Return a dictionary of HTML attributes to be added to the `<tr>`
        element for the supplied `obj` when rendering the results table in
        `index_view`. `data-object-pk` is already added by default.
        """

    def get_extra_class_names_for_field_col(self, obj, field_name): # -> list[Any]:
        """
        Return a list of additional CSS class names to be added to the table
        cell's `class` attribute when rendering the output of `field_name` for
        `obj` in `index_view`.

        Must always return a list.
        """

    def get_extra_attrs_for_field_col(self, obj, field_name): # -> dict[Any, Any]:
        """
        Return a dictionary of additional HTML attributes to be added to a
        table cell when rendering the output of `field_name` for `obj` in
        `index_view`.

        Must always return a dictionary.
        """

    def get_prepopulated_fields(self, request): # -> dict[Any, Any]:
        """
        Returns a sequence specifying custom prepopulated fields slugs on Create/Edit pages.
        """

    def get_form_fields_exclude(self): # -> list[Any]:
        """
        Returns a list or tuple of fields names to be excluded from Create/Edit pages.
        """

    def get_index_view_extra_css(self): # -> list[Any]:
        ...

    def get_index_view_extra_js(self): # -> list[Any]:
        ...

    def get_form_view_extra_css(self): # -> list[Any]:
        ...

    def get_form_view_extra_js(self): # -> list[Any]:
        ...

    def get_inspect_view_extra_css(self): # -> list[Any]:
        ...

    def get_inspect_view_extra_js(self): # -> list[Any]:
        ...

    def get_inspect_view_fields(self): # -> list[Any]:
        """
        Return a list of field names, indicating the model fields that
        should be displayed in the 'inspect' view. Returns the value of the
        'inspect_view_fields' attribute if populated, otherwise a sensible
        list of fields is generated automatically, with any field named in
        'inspect_view_fields_exclude' not being included.
        """

    def index_view(self, request): # -> HttpResponseBase:
        """
        Instantiates a class-based view to provide listing functionality for
        the assigned model. The view class used can be overridden by changing
        the 'index_view_class' attribute.
        """

    def create_view(self, request): # -> HttpResponseBase:
        """
        Instantiates a class-based view to provide 'creation' functionality for
        the assigned model, or redirect to Wagtail's create view if the
        assigned model extends 'Page'. The view class used can be overridden by
        changing the 'create_view_class' attribute.
        """

    def choose_parent_view(self, request): # -> HttpResponseBase:
        """
        Instantiates a class-based view to allows a parent page to be chosen
        for a new object, where the assigned model extends Wagtail's Page
        model, and there is more than one potential parent for new instances.
        The view class used can be overridden by changing the
        'choose_parent_view_class' attribute.
        """

    def inspect_view(self, request, instance_pk): # -> HttpResponseBase:
        """
        Instantiates a class-based view to provide 'inspect' functionality for
        the assigned model. The view class used can be overridden by changing
        the 'inspect_view_class' attribute.
        """
        ...

    def edit_view(self, request, instance_pk): # -> HttpResponseBase:
        """
        Instantiates a class-based view to provide 'edit' functionality for the
        assigned model, or redirect to Wagtail's edit view if the assigned
        model extends 'Page'. The view class used can be overridden by changing
        the  'edit_view_class' attribute.
        """
        ...

    def delete_view(self, request, instance_pk): # -> HttpResponseBase:
        """
        Instantiates a class-based view to provide 'delete confirmation'
        functionality for the assigned model, or redirect to Wagtail's delete
        confirmation view if the assigned model extends 'Page'. The view class
        used can be overridden by changing the 'delete_view_class'
        attribute.
        """
        ...

    def history_view(self, request, instance_pk): # -> HttpResponseBase:
        ...

    def get_edit_handler(self): # -> ObjectList[Model, WagtailAdminModelForm[Model, AbstractBaseUser]]:
        """
        Returns the appropriate edit_handler for this modeladmin class.
        edit_handlers can be defined either on the model itself or on the
        modeladmin (as property edit_handler or panels). Falls back to
        extracting panel / edit handler definitions from the model class.
        """
        ...

    def get_templates(self, action=...): # -> list[str]:
        """
        Utility function that provides a list of templates to try for a given
        view, when the template isn't overridden by one of the template
        attributes on the class.
        """
        ...

    def get_index_template(self): # -> str | list[str]:
        """
        Returns a template to be used when rendering 'index_view'. If a
        template is specified by the 'index_template_name' attribute, that will
        be used. Otherwise, a list of preferred template names are returned.
        """
        ...

    def get_choose_parent_template(self): # -> str | list[str]:
        """
        Returns a template to be used when rendering 'choose_parent_view'. If a
        template is specified by the 'choose_parent_template_name' attribute,
        that will be used. Otherwise, a list of preferred template names are
        returned.
        """
        ...

    def get_inspect_template(self): # -> str | list[str]:
        """
        Returns a template to be used when rendering 'inspect_view'. If a
        template is specified by the 'inspect_template_name' attribute, that
        will be used. Otherwise, a list of preferred template names are
        returned.
        """
        ...

    def get_history_template(self): # -> str | list[str]:
        """
        Returns a template to be used when rendering 'history_view'. If a
        template is specified by the 'history_template_name' attribute, that
        will be used. Otherwise, a list of preferred template names are
        returned.
        """
        ...

    def get_create_template(self): # -> str | list[str]:
        """
        Returns a template to be used when rendering 'create_view'. If a
        template is specified by the 'create_template_name' attribute,
        that will be used. Otherwise, a list of preferred template names are
        returned.
        """
        ...

    def get_edit_template(self): # -> str | list[str]:
        """
        Returns a template to be used when rendering 'edit_view'. If a template
        is specified by the 'edit_template_name' attribute, that will be used.
        Otherwise, a list of preferred template names are returned.
        """
        ...

    def get_delete_template(self): # -> str | list[str]:
        """
        Returns a template to be used when rendering 'delete_view'. If
        a template is specified by the 'delete_template_name'
        attribute, that will be used. Otherwise, a list of preferred template
        names are returned.
        """
        ...

    def get_menu_item(self, order=...): # -> ModelAdminMenuItem:
        """
        Utilised by Wagtail's 'register_menu_item' hook to create a menu item
        to access the listing view, or can be called by ModelAdminGroup
        to create a submenu
        """
        ...

    def get_permissions_for_registration(self): # -> QuerySet[Permission, Permission]:
        """
        Utilised by Wagtail's 'register_permissions' hook to allow permissions
        for a model to be assigned to groups in settings. This is only required
        if the model isn't a Page model, and isn't registered as a Snippet
        """
        ...

    def get_admin_urls_for_registration(self): # -> tuple[URLPattern, ...] | tuple[URLPattern, URLPattern, URLPattern, URLPattern, URLPattern] | tuple[URLPattern, URLPattern, URLPattern, URLPattern]:
        """
        Utilised by Wagtail's 'register_admin_urls' hook to register urls for
        our the views that class offers.
        """
        ...

    def will_modify_explorer_page_queryset(self): # -> bool:
        ...

    def modify_explorer_page_queryset(self, parent_page, queryset, request):
        ...

    def register_with_wagtail(self): # -> None:
        ...

    def register_admin_url_finders(self): # -> None:
        ...

    def register_indexing(self): # -> None:
        ...



class ModelAdminGroup(WagtailRegisterable):
    """
    Acts as a container for grouping together mutltiple PageModelAdmin and
    SnippetModelAdmin instances. Creates a menu item with a submenu for
    accessing the listing pages of those instances
    """
    items = ...
    menu_label = ...
    menu_item_name = ...
    menu_order = ...
    menu_icon = ...
    def __init__(self) -> None:
        """
        When initialising, instantiate the classes within 'items', and assign
        the instances to a 'modeladmin_instances' attribute for convenient
        access later
        """
        ...

    def get_menu_label(self): # -> Literal['']:
        ...

    def get_menu_item_name(self): # -> None:
        ...

    def get_app_label_from_subitems(self): # -> Literal['']:
        ...

    def get_menu_icon(self): # -> Literal['folder-open-inverse']:
        ...

    def get_menu_order(self): # -> Literal[999]:
        ...

    def get_menu_item(self): # -> GroupMenuItem | None:
        """
        Utilised by Wagtail's 'register_menu_item' hook to create a menu
        for this group with a submenu linking to listing pages for any
        associated ModelAdmin instances
        """
        ...

    def get_submenu_items(self): # -> list[Any]:
        ...

    def get_permissions_for_registration(self): # -> QuerySet[Permission, Permission]:
        """
        Utilised by Wagtail's 'register_permissions' hook to allow permissions
        for a all models grouped by this class to be assigned to Groups in
        settings.
        """
        ...

    def get_admin_urls_for_registration(self): # -> tuple[()]:
        """
        Utilised by Wagtail's 'register_admin_urls' hook to register urls for
        used by any associated ModelAdmin instances
        """
        ...

    def will_modify_explorer_page_queryset(self): # -> bool:
        ...

    def modify_explorer_page_queryset(self, parent_page, queryset, request):
        ...

    def register_with_wagtail(self): # -> None:
        ...

    def register_admin_url_finders(self): # -> None:
        ...

    def register_indexing(self): # -> None:
        ...



def modeladmin_register[AdminT: ModelAdmin[Any]](modeladmin_class: type[AdminT]) -> type[AdminT]:
    """
    Method for registering ModelAdmin or ModelAdminGroup classes with Wagtail.
    """
