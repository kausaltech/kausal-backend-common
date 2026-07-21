import collections
from collections.abc import Generator, Sequence
from typing import Any

from django.core.exceptions import ValidationError
from django.utils.functional import cached_property
from django_stubs_ext import StrOrPromise
from wagtail.telepath import Adapter

from _typeshed import Incomplete

from .base import BaseBlock, Block, BlockMeta, BoundBlock, DeclarativeSubBlocksMetaclass

class StructBlockValidationError(ValidationError):
    non_block_errors: Incomplete
    block_errors: Incomplete
    def __init__(self, block_errors: Incomplete | None = None, non_block_errors: Incomplete | None = None) -> None: ...
    def as_json_data(self): ...


class BlockGroup:
    """
    A grouping of blocks within a :class:`StructBlock`'s form layout in the
    editing interface. Can be used directly as the ``form_layout`` in
    :class:`StructBlock`.Meta, or nested within another ``BlockGroup``.
    """

    def __init__(
        self,
        children: list[str | BlockGroup],
        settings: list[str | BlockGroup] | None = None,
        heading: StrOrPromise = ...,
        classname: str = ...,
        help_text: StrOrPromise = ...,
        icon: str = ...,
        attrs: dict[str, str] | None = None,
        label_format: str | None = None,
    ):
        """
        :param children: A list of block names or nested ``BlockGroup`` that will be
            rendered in the main content area.
        :type children: list[str | BlockGroup]

        :param settings: A list of block names or nested ``BlockGroup`` that will be
            rendered in the collapsible "settings" area that is hidden by default.
        :type settings: list[str | BlockGroup]

        The following attributes are only used when the ``BlockGroup`` is nested within
        another ``BlockGroup``. For the top-level ``BlockGroup`` used as
        ``Meta.form_layout`` in a :class:`StructBlock`, these attributes are ignored in
        favor of the corresponding attributes on ``StructBlock.Meta``.

        :param heading: The heading label of the collapsible panel for this block
            group. For a top-level group, the ``StructBlock``'s ``label`` will be
            used instead.
        :type heading: str

        :param classname: Additional CSS class name(s) to add to the block group's main
            content area. To set the group to be initially collapsed, include the
            ``collapsed`` class here.
        :type classname: str

        :param help_text: Help text to display below the block group's heading.
        :type help_text: str

        :param icon: The name of the icon to display alongside the block group's heading.
        :type icon: str

        :param attrs: A dictionary of HTML attributes to add to the block group's main content area.
        :type attrs: dict

        :param label_format: The summary label shown after the ``heading`` when the
            block is collapsed in the editing interface. By default, the value of the
            first child block is shown, but this can be customized by setting a string
            here with block names contained in braces - for example ``label_format = "
            {surname}, {first_name}"``. If you wish to hide the summary label entirely,
            set this to the empty string ``""``.
        :type label_format: str | None
        """

    telepath_adapter_name: str

    @cached_property
    def unique_children_and_settings(self) -> tuple[list[tuple[Block, str]], list[tuple[Block, str]]]: ...

    def get_sorted_block_names(self) -> list[str]:
        """
        Return a flat list of all block names in this ``BlockGroup`` and any
        nested ``BlockGroups`` in the group's list order.
        """

    def js_opts(self) -> dict[str, Any]: ...

    def telepath_pack(self, context: dict[str, Any] | None = None) -> tuple[str, list[dict[str, Any]]]: ...


class StructValue[B: StructBlock = StructBlock](collections.OrderedDict[str, Block]):
    """A class that generates a StructBlock value from provided sub-blocks"""

    block: B
    def __init__(self, block: B, *args) -> None: ...
    def __html__(self): ...
    def render_as_block(self, context: Incomplete | None = None): ...
    @cached_property
    def bound_blocks(self) -> collections.OrderedDict[str, BoundBlock]: ...
    def __reduce__(self): ...

class PlaceholderBoundBlock(BoundBlock):
    """
    Provides a render_form method that outputs a block placeholder, for use in custom form_templates
    """
    def render_form(self): ...

class BaseStructBlock[M: BlockMeta = BlockMeta](Block[M]):
    search_index: bool
    child_blocks: collections.OrderedDict[str, Block]
    def __init__(
        self, local_blocks: Sequence[tuple[str, Block[Any] | BaseBlock]] | None = None, search_index: bool = True, **kwargs
    ) -> None: ...
    @classmethod
    def construct_from_lookup(cls, lookup, child_blocks, **kwargs): ...  # noqa: ANN206 type stubs
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

class StructBlock[M: BlockMeta = BlockMeta](BaseStructBlock[M], metaclass=DeclarativeSubBlocksMetaclass): ...

class StructBlockAdapter(Adapter):
    js_constructor: str
    def js_args(self, block): ...
    @cached_property
    def media(self): ...
