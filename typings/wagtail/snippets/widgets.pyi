from django.db.models import Model
from django.forms.widgets import Media
from django.utils.functional import cached_property as cached_property
from django_stubs_ext import StrOrPromise
from wagtail.admin.staticfiles import versioned_static as versioned_static
from wagtail.admin.widgets import BaseChooser as BaseChooser, BaseChooserAdapter as BaseChooserAdapter
from wagtail.admin.widgets.button import ListingButton as ListingButton
from wagtail.telepath import register as register

class AdminSnippetChooser(BaseChooser):
    display_title_key: str
    classname: str
    js_constructor: str
    model: Model
    choose_one_text: StrOrPromise
    choose_another_text: StrOrPromise
    link_to_chosen_text: StrOrPromise
    def __init__(self, model: Model, **kwargs) -> None: ...
    def get_chooser_modal_url(self): ...
    @cached_property
    def media(self) -> Media: ...

class SnippetChooserAdapter(BaseChooserAdapter):
    js_constructor: str
    @cached_property
    def media(self) -> Media: ...

class SnippetListingButton(ListingButton): ...
