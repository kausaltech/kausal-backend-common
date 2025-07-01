from wagtail.admin.panels import FieldPanel
from wagtail_color_panel.widgets import ColorInputWidget as ColorInputWidget, PolyfillColorInputWidget as PolyfillColorInputWidget

class NativeColorPanel(FieldPanel):
    def get_form_options(self): ...

class PolyfillColorPanel(FieldPanel):
    def get_form_options(self): ...
