import collections
from collections.abc import Generator
from typing import Any, Sequence

from django.core.exceptions import ValidationError
from django.utils.functional import cached_property
from wagtail.telepath import Adapter

from _typeshed import Incomplete

from .base import BaseBlock, Block, BoundBlock, DeclarativeSubBlocksMetaclass

class StructBlockValidationError(ValidationError):
    non_block_errors: Incomplete
    block_errors: Incomplete
    def __init__(self, block_errors: Incomplete | None = None, non_block_errors: Incomplete | None = None) -> None: ...
    def as_json_data(self): ...

class StructValue(collections.OrderedDict):
    """A class that generates a StructBlock value from provided sub-blocks"""
    block: Incomplete
    def __init__(self, block, *args) -> None: ...
    def __html__(self): ...
    def render_as_block(self, context: Incomplete | None = None): ...
    @cached_property
    def bound_blocks(self): ...
    def __reduce__(self): ...

class PlaceholderBoundBlock(BoundBlock):
    """
    Provides a render_form method that outputs a block placeholder, for use in custom form_templates
    """
    def render_form(self): ...

class BaseStructBlock(Block):
    search_index: Incomplete
    child_blocks: Incomplete
    def __init__(self, local_blocks: Sequence[tuple[str, Block[Any] | BaseBlock]] | None = None, search_index: bool = True, **kwargs) -> None: ...
    @classmethod
    def construct_from_lookup(cls, lookup, child_blocks, **kwargs): ...
    def get_default(self):
        """
        Any default value passed in the constructor or self.meta is going to be a dict
        rather than a StructValue; for consistency, we need to convert it to a StructValue
        for StructBlock to work with
        """
    def value_from_datadict(self, data, files, prefix): ...
    def value_omitted_from_data(self, data, files, prefix): ...
    def clean(self, value): ...
    def to_python(self, value):
        """Recursively call to_python on children and return as a StructValue"""
    def bulk_to_python(self, values): ...
    def get_prep_value(self, value):
        """Recursively call get_prep_value on children and return as a plain dict"""
    def normalize(self, value): ...
    def get_form_state(self, value): ...
    def get_api_representation(self, value, context: Incomplete | None = None):
        """Recursively call get_api_representation on children and return as a plain dict"""
    def get_searchable_content(self, value): ...
    def extract_references(self, value) -> Generator[Incomplete]: ...
    def get_block_by_content_path(self, value, path_elements):
        """
        Given a list of elements from a content path, retrieve the block at that path
        as a BoundBlock object, or None if the path does not correspond to a valid block.
        """
    def deconstruct(self):
        """
        Always deconstruct StructBlock instances as if they were plain StructBlocks with all of the
        field definitions passed to the constructor - even if in reality this is a subclass of StructBlock
        with the fields defined declaratively, or some combination of the two.

        This ensures that the field definitions get frozen into migrations, rather than leaving a reference
        to a custom subclass in the user's models.py that may or may not stick around.
        """
    def deconstruct_with_lookup(self, lookup): ...
    def check(self, **kwargs): ...
    def render_basic(self, value, context: Incomplete | None = None): ...
    def render_form_template(self): ...
    def get_form_context(self, value, prefix: str = '', errors: Incomplete | None = None): ...
    class Meta:
        default: Incomplete
        form_classname: str
        form_template: Incomplete
        value_class = StructValue
        label_format: Incomplete
        icon: str

class StructBlock(BaseStructBlock, metaclass=DeclarativeSubBlocksMetaclass): ...

class StructBlockAdapter(Adapter):
    js_constructor: str
    def js_args(self, block): ...
    @cached_property
    def media(self): ...
