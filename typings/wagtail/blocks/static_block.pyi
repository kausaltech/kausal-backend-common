from .base import Block
from _typeshed import Incomplete
from django.utils.functional import cached_property
from wagtail.telepath import Adapter

__all__ = ['StaticBlock']

class StaticBlock(Block):
    """
    A block that just 'exists' and has no fields.
    """
    def get_admin_text(self): ...
    def value_from_datadict(self, data, files, prefix) -> None: ...
    def normalize(self, value) -> None: ...
    class Meta:
        admin_text: Incomplete
        default: Incomplete

class StaticBlockAdapter(Adapter):
    js_constructor: str
    def js_args(self, block): ...
    @cached_property
    def media(self): ...
