from django.db.models import Model
from django.utils.functional import cached_property as cached_property
from django_stubs_ext import StrOrPromise
from wagtail.admin.forms.models import register_form_field_override as register_form_field_override
from wagtail.admin.widgets.chooser import BaseChooser as BaseChooser
from wagtail.blocks import ChooserBlock as ChooserBlock

from _typeshed import Incomplete

from .base import ViewSet as ViewSet

class ChooserViewSet[M: Model](ViewSet):
    model: type[M]
    choose_one_text: StrOrPromise
    choose_another_text: StrOrPromise
    edit_item_text: StrOrPromise
    per_page: object | int
    preserve_url_parameters: Incomplete
    url_filter_parameters: Incomplete
    choose_view_class: Incomplete
    choose_results_view_class: Incomplete
    chosen_view_class: Incomplete
    chosen_multiple_view_class: Incomplete
    create_view_class: Incomplete
    base_widget_class = BaseChooser
    widget_telepath_adapter_class: Incomplete
    base_block_class = ChooserBlock
    register_widget: bool
    creation_form_class: Incomplete
    form_fields: Incomplete
    exclude_form_fields: Incomplete
    search_tab_label: Incomplete
    create_action_label: Incomplete
    create_action_clicked_label: Incomplete
    creation_tab_label: Incomplete
    permission_policy: Incomplete
    def __init__(self, *args, **kwargs) -> None: ...
    def get_common_view_kwargs(self, **kwargs): ...
    @property
    def choose_view(self): ...
    @property
    def choose_results_view(self): ...
    @property
    def chosen_view(self): ...
    @property
    def chosen_multiple_view(self): ...
    @property
    def create_view(self): ...
    @cached_property
    def model_name(self): ...
    @cached_property
    def widget_class(self): ...
    def get_block_class(self, name=None, module_path=None): ...
    def get_urlpatterns(self): ...
    def on_register(self) -> None: ...
