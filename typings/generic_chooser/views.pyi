from collections.abc import Generator, Iterable
from typing import Any

from django.core.paginator import Paginator
from django.db.models.base import Model
from django.db.models.query import QuerySet
from django.http.request import HttpRequest
from django.views import View
from django.views.generic.base import ContextMixin
from wagtail.admin.viewsets.base import ViewSet

from _typeshed import Incomplete

class ModalPageFurnitureMixin(ContextMixin):
    """
    Add icon and page title to the template context
    """
    icon: Incomplete
    page_title: Incomplete
    def get_context_data(self, **kwargs): ...

class ChooserMixin:
    """
    Helper methods common to all sub-views of the chooser modal. Will be subclassed to implement
    different data sources (e.g. database versus REST API).
    """
    preserve_url_parameters: Incomplete
    def get_object(self, pk) -> Any:
        """
        Return the object corresponding to the given ID. Both 'object' and 'ID' are loosely defined
        here; for example, this may be a JSON API lookup returning a dict, rather than a database
        lookup returning a model instance. Any object type is fine as long as the other methods
        here (get_object_string etc) provide consistent behaviour on it, and the ID is a simple
        value that can be embedded into a URL.
        """
    def get_object_string(self, instance):
        """
        Return a string representation of the given object instance
        """
    def get_object_id(self, instance) -> None:
        """
        Return the ID for the given object instance
        """
    choose_url_name: Incomplete
    def get_choose_url_parameters(self): ...
    def get_choose_url(self): ...
    chosen_url_name: Incomplete
    def get_chosen_url_parameters(self): ...
    def get_chosen_url(self, instance): ...
    chosen_multiple_url_name: Incomplete
    def get_chosen_multiple_url(self): ...
    edit_item_url_name: Incomplete
    def get_edit_item_url(self, instance): ...
    permission_policy: Incomplete
    def get_permission_policy(self): ...
    def user_can_create(self, user):
        """
        Return True iff the given user has permission to create objects of the type being
        chosen here
        """
    def get_object_list(self, **kwargs) -> Iterable[Any]:
        """
        Return an iterable consisting of all the choosable object instances.
        kwargs contains parameters that may be used to modify the result set; currently the only
        one available is 'search_term', passed when is_searchable is True.
        """
    per_page: Incomplete
    def get_paginated_object_list(self, page_number, **kwargs):
        """
        Return a page of results according to the `page_number` attribute, as a tuple of
        an iterable sequence of instances and a Paginator object
        """
    is_searchable: bool
    prefix: Incomplete
    def get_prefix(self): ...
    def get_chosen_response_data(self, item):
        """
        Generate the result value to be returned when an object has been chosen
        """
    def get_multiple_chosen_response(self, items): ...
    def get_chosen_response(self, item):
        """
        Return the HTTP response to indicate that an object has been chosen
        """

class ModelChooserMixin[M: Model, QS: QuerySet[Any] = QuerySet[Model]](ChooserMixin):
    """Mixin for chooser modals backed by the database / ORM"""
    model: type[M]
    order_by: Incomplete
    permission_policy: Incomplete
    request: HttpRequest
    def get_permission_policy(self): ...
    def get_unfiltered_object_list(self) -> QS: ...
    def get_object_list(self, search_term=None, **kwargs) -> Iterable[M]: ...
    def get_object(self, pk) -> M: ...
    def get_object_id(self, instance) -> Any: ...
    prefix: Incomplete
    def get_prefix(self): ...

class DRFChooserMixin(ChooserMixin):
    """Mixin for chooser modals backed by a Django REST Framework API"""
    api_base_url: Incomplete
    title_field_name: Incomplete
    def get_api_parameters(self, search_term=None, **kwargs): ...
    def get_object_list(self, **kwargs): ...
    def get_paginated_object_list(self, page_number, **kwargs): ...
    def get_object_id(self, item): ...
    def get_object_string(self, item): ...
    def get_object(self, id): ...

class ChooserListingTabMixin:
    search_placeholder: Incomplete
    listing_tab_label: Incomplete
    listing_tab_template: str
    results_template: str
    def get_page_number_from_url(self): ...
    def get_search_form(self): ...
    def get_rows(self) -> Generator[Incomplete]: ...
    def get_row_data(self, item): ...
    def get_results_template(self): ...
    def get_listing_tab_template(self): ...
    search_form: Incomplete
    is_paginated: Incomplete
    object_list: Incomplete
    def get_listing_tab_context_data(self): ...

class ChooserCreateTabMixin:
    create_tab_label: Incomplete
    create_tab_template: str
    create_form_submit_label: Incomplete
    create_form_is_long_running: bool
    create_form_submitted_label: Incomplete
    initial: Incomplete
    form_class: Incomplete
    def get_initial(self):
        """Return the initial data to use for forms on this view."""
    def get_form_class(self): ...
    def get_form(self, form_class=None):
        """Return an instance of the form to be used in this view."""
    def get_form_kwargs(self):
        """Return the keyword arguments for instantiating the form."""
    def create_form_is_available(self): ...
    def form_valid(self, form) -> None:
        """
        Called when a valid form submission is received; returns the created object
        """
    def get_create_tab_context_data(self): ...

class ModelChooserCreateTabMixin[M: Model](ChooserCreateTabMixin):
    model: type[M]
    request: HttpRequest
    fields: Incomplete
    create_form_submit_label: Incomplete
    def __init__(self, *args, **kwargs) -> None: ...
    form_class: Incomplete
    def get_form_class(self): ...
    def form_valid(self, form):
        """
        Called when a valid form submission is received; returns the created object
        """

class DRFChooserCreateTabMixin(ChooserCreateTabMixin):
    def form_valid(self, form): ...

class BaseChooseView(ModalPageFurnitureMixin, ContextMixin, View):
    icon: str
    page_title: Incomplete
    template: str
    def get_template(self): ...
    form: Incomplete
    def get(self, request): ...
    def post(self, request): ...
    def get_context_data(self, results_only: bool = False, **kwargs): ...

class ModelChooseView[M: Model](ChooserMixin, ChooserListingTabMixin, ModelChooserCreateTabMixin[M], BaseChooseView): ...

class APIPaginator[T](Paginator[T]):
    """
    Customisation of Django's Paginator to give us access to the page_range / num_pages
    functionality needed by pagination UI, without having to use Paginator's
    list-slicing logic - which isn't a good fit for API use, as it relies on knowing
    the total count of results before deciding which slice to request.

    Rather than instantiating it with a list/queryset and page number, we pass it the
    full item count, which is sufficient for page_range / num_pages to work.
    """
    def __init__(self, count, per_page, **kwargs) -> None: ...

class DRFChooseView(DRFChooserMixin, ChooserListingTabMixin, DRFChooserCreateTabMixin, BaseChooseView): ...

class BaseChosenView(View):
    def get(self, request, pk): ...

class BaseChosenMultipleView(View):
    def get(self, request): ...

class ModelChosenView[M: Model](ModelChooserMixin[M], BaseChosenView): ...
class DRFChosenView(DRFChooserMixin, BaseChosenView): ...

class ChooserViewSet(ViewSet):
    base_choose_view_class = BaseChooseView
    base_chosen_view_class = BaseChosenView
    base_chosen_multiple_view_class = BaseChosenMultipleView
    chooser_mixin_class = ChooserMixin
    listing_tab_mixin_class = ChooserListingTabMixin
    create_tab_mixin_class = ChooserCreateTabMixin
    choose_view_class: Incomplete
    chosen_view_class: Incomplete
    chosen_multiple_view_class: Incomplete
    request: HttpRequest

    def __init__(self, *args, **kwargs) -> None: ...
    def get_choose_view_attrs(self): ...
    @property
    def choose_view(self): ...
    def get_chosen_view_attrs(self): ...
    @property
    def chosen_view(self): ...
    def get_chosen_multiple_view_attrs(self): ...
    @property
    def chosen_multiple_view(self): ...
    def get_urlpatterns(self): ...

class ModelChooserViewSet[M: Model](ChooserViewSet):
    chooser_mixin_class: type[ModelChooserMixin[Any, Any]]
    create_tab_mixin_class: type[ModelChooserCreateTabMixin[Any]]
    def get_choose_view_attrs(self): ...
    def get_chosen_view_attrs(self): ...
    def get_chosen_multiple_view_attrs(self): ...

class DRFChooserViewSet(ChooserViewSet):
    chooser_mixin_class = DRFChooserMixin
    create_tab_mixin_class = DRFChooserCreateTabMixin
    def get_choose_view_attrs(self): ...
    def get_chosen_view_attrs(self): ...
    def get_chosen_multiple_view_attrs(self): ...
