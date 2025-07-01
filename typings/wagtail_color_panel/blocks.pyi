from _typeshed import Incomplete
from django.utils.functional import cached_property as cached_property
from wagtail.blocks import FieldBlock
from wagtail_color_panel.validators import hex_triplet_validator as hex_triplet_validator
from wagtail_color_panel.widgets import ColorInputWidget as ColorInputWidget

class NativeColorBlock(FieldBlock):
    field_options: Incomplete
    def __init__(self, required: bool = True, help_text: Incomplete | None = None, validators=(), **kwargs) -> None: ...
    @cached_property
    def field(self): ...
    class Meta:
        icon: str
