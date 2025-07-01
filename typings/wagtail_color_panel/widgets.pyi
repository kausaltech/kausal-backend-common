from _typeshed import Incomplete
from django.forms import widgets
from wagtail.widget_adapters import WidgetAdapter

class PolyfillColorInputWidget(widgets.TextInput):
    class Media:
        css: Incomplete
        js: Incomplete
    def render(self, name, value, attrs: Incomplete | None = None, renderer: Incomplete | None = None): ...

class ColorInputWidget(widgets.TextInput):
    template_name: str
    def __init__(self, attrs: Incomplete | None = None) -> None: ...
    def build_attrs(self, *args, **kwargs): ...
    @property
    def media(self): ...

class ColorInputWidgetAdapter(WidgetAdapter):
    js_constructor: str
    class Media:
        js: Incomplete
