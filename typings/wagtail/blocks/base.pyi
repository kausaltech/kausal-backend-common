# ruff: noqa: D400, D415, D205, D401, D200, D204
from collections.abc import Iterable
from typing import Any, ClassVar, Generic, Mapping, OrderedDict, Protocol, Self, TypeVar, type_check_only

from django import forms
from django.core.files.base import File
from django.forms.utils import ErrorList
from django.forms.widgets import Media
from django.utils.functional import cached_property
from django_stubs_ext import StrOrPromise

from _typeshed import Incomplete

from .definition_lookup import BlockDefinitionLookup

__all__ = ['BaseBlock', 'Block', 'BoundBlock', 'DeclarativeSubBlocksMetaclass', 'BlockWidget', 'BlockField']

class BaseBlock(type):
    def __new__(mcs, name, bases, attrs): ...  # noqa: N804

@type_check_only
class BlockMeta(Protocol):
    label: StrOrPromise | None = None
    icon: str = ''
    classname: str | None = None
    group: str = ''

BlockMetaT = TypeVar('BlockMetaT', bound=BlockMeta, default=BlockMeta)  # noqa: PYI001


class Block(Generic[BlockMetaT],metaclass=BaseBlock):
    name: str
    creation_counter: int
    TEMPLATE_VAR: str

    Meta: type[Any]
    # class Meta:
    #     label: StrOrPromise | None
    #     icon: str
    #     classname: str | None
    #     group: str

    MUTABLE_META_ATTRIBUTES: ClassVar[list[str]]
    def __new__(cls, *args, **kwargs): ...
    meta: BlockMetaT
    definition_prefix: str
    label: StrOrPromise | None
    def __init__(self, **kwargs) -> None: ...
    @classmethod
    def construct_from_lookup(cls, lookup: BlockDefinitionLookup, *args, **kwargs) -> Self:
        """
        See `wagtail.blocks.definition_lookup.BlockDefinitionLookup`.
        Construct a block instance from the provided arguments, using the given BlockDefinitionLookup
        object to perform any necessary lookups.
        """
    def set_name(self, name) -> None: ...
    def set_meta_options(self, opts) -> None:
        """
        Update this block's meta options (out of the ones designated as mutable) from the given dict.
        Used by the StreamField constructor to pass on kwargs that are to be handled by the block,
        since the block object has already been created by that point, e.g.:
        body = StreamField(SomeStreamBlock(), max_num=5)
        """
    def value_from_datadict(self, data: Mapping[str, Any], files: Mapping[str, Iterable[File]], prefix: str) -> None: ...
    def value_omitted_from_data(self, data: Mapping[str, Any], files: Mapping[str, Iterable[File]], name: str) -> bool:
        """
        Used only for top-level blocks wrapped by BlockWidget (i.e.: typically only StreamBlock)
        to inform ModelForm logic on Django >=1.10.2 whether the field is absent from the form
        submission (and should therefore revert to the field default).
        """
    def bind(self, value, prefix: str | None = None, errors: ErrorList | None = None) -> BoundBlock:
        """
        Return a BoundBlock which represents the association of this block definition with a value
        and a prefix (and optionally, a ValidationError to be rendered).
        BoundBlock primarily exists as a convenience to allow rendering within templates:
        bound_block.render() rather than blockdef.render(value, prefix) which can't be called from
        within a template.
        """
    def get_default(self):
        """
        Return this block's default value (conventionally found in self.meta.default),
        converted to the value type expected by this block. This caters for the case
        where that value type is not something that can be expressed statically at
        model definition time (e.g. something like StructValue which incorporates a
        pointer back to the block definition object).
        """
    def clean(self, value):
        """
        Validate value and return a cleaned version of it, or throw a ValidationError if validation fails.
        The thrown ValidationError instance will subsequently be passed to render() to display the
        error message; the ValidationError must therefore include all detail necessary to perform that
        rendering, such as identifying the specific child block(s) with errors, in the case of nested
        blocks. (It is suggested that you use the 'params' attribute for this; using error_list /
        error_dict is unreliable because Django tends to hack around with these when nested.)
        """
    def normalize(self, value):
        """
        Given a value for any acceptable type for this block (e.g. string or RichText for a RichTextBlock;
        dict or StructValue for a StructBlock), return a value of the block's native type (e.g. RichText
        for RichTextBlock, StructValue for StructBlock). In simple cases this will return the value
        unchanged.
        """
    def to_python(self, value):
        """
        Convert 'value' from a simple (JSON-serialisable) value to a (possibly complex) Python value to be
        used in the rest of the block API and within front-end templates . In simple cases this might be
        the value itself; alternatively, it might be a 'smart' version of the value which behaves mostly
        like the original value but provides a native HTML rendering when inserted into a template; or it
        might be something totally different (e.g. an image chooser will use the image ID as the clean
        value, and turn this back into an actual image object here).

        For blocks that are usable at the top level of a StreamField, this must also accept any type accepted
        by normalize. (This is because Django calls `Field.to_python` from `Field.clean`.)
        """
    def bulk_to_python(self, values):
        """
        Apply the to_python conversion to a list of values. The default implementation simply
        iterates over the list; subclasses may optimise this, e.g. by combining database lookups
        into a single query.
        """
    def get_prep_value(self, value):
        """
        The reverse of to_python; convert the python value into JSON-serialisable form.
        """
    def get_form_state(self, value):
        """
        Convert a python value for this block into a JSON-serialisable representation containing
        all the data needed to present the value in a form field, to be received by the block's
        client-side component. Examples of where this conversion is not trivial include rich text
        (where it needs to be supplied in a format that the editor can process, e.g. ContentState
        for Draftail) and page / image / document choosers (where it needs to include all displayed
        data for the selected item, such as title or thumbnail).
        """
    def get_context(self, value, parent_context: Incomplete | None = None):
        """
        Return a dict of context variables (derived from the block value and combined with the parent_context)
        to be used as the template context when rendering this value through a template.
        """
    def get_template(self, value: Incomplete | None = None, context: Incomplete | None = None):
        """
        Return the template to use for rendering the block if specified on meta class.
        This extraction was added to make dynamic templates possible if you override this method

        value contains the current value of the block, allowing overridden methods to
        select the proper template based on the actual block value.
        """
    def render(self, value, context: Incomplete | None = None):
        """
        Return a text rendering of 'value', suitable for display on templates. By default, this will
        use a template (with the passed context, supplemented by the result of get_context) if a
        'template' property is specified on the block, and fall back on render_basic otherwise.
        """
    def get_api_representation(self, value, context: Incomplete | None = None):
        """
        Can be used to customise the API response and defaults to the value returned by get_prep_value.
        """
    def render_basic(self, value, context: Incomplete | None = None):
        """
        Return a text rendering of 'value', suitable for display on templates. render() will fall back on
        this if the block does not define a 'template' property.
        """
    def get_searchable_content(self, value):
        """
        Returns a list of strings containing text content within this block to be used in a search engine.
        """
    def extract_references(self, value): ...
    def get_block_by_content_path(self, value, path_elements):
        """
        Given a list of elements from a content path, retrieve the block at that path
        as a BoundBlock object, or None if the path does not correspond to a valid block.
        """
    def check(self, **kwargs):
        """
        Hook for the Django system checks framework -
        returns a list of django.core.checks.Error objects indicating validity errors in the block
        """
    def id_for_label(self, prefix: str) -> str | None:
        """
        Return the ID to be used as the 'for' attribute of <label> elements that refer to this block,
        when the given field prefix is in use. Return None if no 'for' attribute should be used.
        """
    @property
    def required(self):
        """
        Flag used to determine whether labels for this block should display a 'required' asterisk.
        False by default, since Block does not provide any validation of its own - it's up to subclasses
        to define what required-ness means.
        """
    @cached_property
    def canonical_module_path(self):
        """
        Return the module path string that should be used to refer to this block in migrations.
        """
    def deconstruct(self): ...
    def deconstruct_with_lookup(self, lookup):
        """
        Like `deconstruct`, but with a `wagtail.blocks.definition_lookup.BlockDefinitionLookupBuilder`
        object available so that any block instances within the definition can be added to the lookup
        table to obtain an ID (potentially shared with other matching block definitions, thus reducing
        the overall definition size) to be used in place of the block. The resulting deconstructed form
        returned here can then be restored into a block object using `Block.construct_from_lookup`.
        """
    def __eq__(self, other):
        """
        Implement equality on block objects so that two blocks with matching definitions are considered
        equal. Block objects are intended to be immutable with the exception of set_name() and any meta
        attributes identified in MUTABLE_META_ATTRIBUTES, so checking these along with the result of
        deconstruct (which captures the constructor arguments) is sufficient to identify (valid) differences.

        This was implemented as a workaround for a Django <1.9 bug and is quite possibly not used by Wagtail
        any more, but has been retained as it provides a sensible definition of equality (and there's no
        reason to break it).
        """

class BoundBlock:
    block: Block[Any]
    value: Incomplete
    prefix: Incomplete
    errors: Incomplete
    def __init__(self, block, value, prefix: Incomplete | None = None, errors: Incomplete | None = None) -> None: ...
    def render(self, context: Incomplete | None = None): ...
    def render_as_block(self, context: Incomplete | None = None):
        """
        Alias for render; the include_block tag will specifically check for the presence of a method
        with this name. (This is because {% include_block %} is just as likely to be invoked on a bare
        value as a BoundBlock. If we looked for a `render` method instead, we'd run the risk of finding
        an unrelated method that just happened to have that name - for example, when called on a
        PageChooserBlock it could end up calling page.render.
        """
    def id_for_label(self): ...

class DeclarativeSubBlocksMetaclass(BaseBlock):
    """
    Metaclass that collects sub-blocks declared on the base classes.
    (cheerfully stolen from https://github.com/django/django/blob/main/django/forms/forms.py)
    """

    declared_blocks: ClassVar[OrderedDict[str, BaseBlock]]
    base_blocks: ClassVar[OrderedDict[str, BaseBlock]]

    def __new__(mcs, name, bases, attrs): ...  # noqa: N804

class BlockWidget(forms.Widget):
    """Wraps a block object as a widget so that it can be incorporated into a Django form"""
    block_def: Incomplete
    def __init__(self, block_def, attrs: Incomplete | None = None) -> None: ...
    @property
    def js_context(self): ...
    @property
    def block_json(self): ...
    def id_for_label(self, prefix: str) -> str: ...
    def render_with_errors(
        self, name, value, attrs: Incomplete | None = None, errors: Incomplete | None = None, renderer: Incomplete | None = None,
    ): ...
    def render(self, name, value, attrs: Incomplete | None = None, renderer: Incomplete | None = None): ...
    @cached_property
    def media(self) -> Media: ...
    def value_from_datadict(self, data, files, name): ...
    def value_omitted_from_data(self, data, files, name): ...

class BlockField(forms.Field):
    """Wraps a block object as a form field so that it can be incorporated into a Django form"""
    block: Incomplete
    def __init__(self, block: Incomplete | None = None, **kwargs) -> None: ...
    def clean(self, value): ...
    def has_changed(self, initial_value, data_value): ...
