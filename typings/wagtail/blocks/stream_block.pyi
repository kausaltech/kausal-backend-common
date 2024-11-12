from .base import Block, BoundBlock, DeclarativeSubBlocksMetaclass
from _typeshed import Incomplete
from collections.abc import Generator, Mapping, MutableSequence
from django.core.exceptions import ValidationError
from django.utils.functional import cached_property
from wagtail.telepath import Adapter

__all__ = ['BaseStreamBlock', 'StreamBlock', 'StreamValue', 'StreamBlockValidationError']

class StreamBlockValidationError(ValidationError):
    non_block_errors: Incomplete
    block_errors: Incomplete
    def __init__(self, block_errors: Incomplete | None = None, non_block_errors: Incomplete | None = None) -> None: ...
    def as_json_data(self): ...

class BaseStreamBlock(Block):
    search_index: Incomplete
    child_blocks: Incomplete
    def __init__(self, local_blocks: Incomplete | None = None, search_index: bool = True, **kwargs) -> None: ...
    @classmethod
    def construct_from_lookup(cls, lookup, child_blocks, **kwargs): ...
    def empty_value(self, raw_text: Incomplete | None = None): ...
    def sorted_child_blocks(self):
        """Child blocks, sorted in to their groups."""
    def grouped_child_blocks(self):
        """
        The available child block types of this stream block, organised into groups according to
        their meta.group attribute.
        Returned as an iterable of (group_name, list_of_blocks) tuples
        """
    def value_from_datadict(self, data, files, prefix): ...
    def value_omitted_from_data(self, data, files, prefix): ...
    @property
    def required(self): ...
    def clean(self, value): ...
    def to_python(self, value): ...
    def bulk_to_python(self, values): ...
    def get_prep_value(self, value): ...
    def normalize(self, value): ...
    def get_form_state(self, value): ...
    def get_api_representation(self, value, context: Incomplete | None = None): ...
    def render_basic(self, value, context: Incomplete | None = None): ...
    def get_searchable_content(self, value): ...
    def extract_references(self, value) -> Generator[Incomplete]: ...
    def get_block_by_content_path(self, value, path_elements):
        """
        Given a list of elements from a content path, retrieve the block at that path
        as a BoundBlock object, or None if the path does not correspond to a valid block.
        """
    def deconstruct(self):
        """
        Always deconstruct StreamBlock instances as if they were plain StreamBlocks with all of the
        field definitions passed to the constructor - even if in reality this is a subclass of StreamBlock
        with the fields defined declaratively, or some combination of the two.

        This ensures that the field definitions get frozen into migrations, rather than leaving a reference
        to a custom subclass in the user's models.py that may or may not stick around.
        """
    def deconstruct_with_lookup(self, lookup): ...
    def check(self, **kwargs): ...
    class Meta:
        icon: str
        default: Incomplete
        required: bool
        form_classname: Incomplete
        min_num: Incomplete
        max_num: Incomplete
        block_counts: Incomplete
        collapsed: bool
    MUTABLE_META_ATTRIBUTES: Incomplete

class StreamBlock(BaseStreamBlock, metaclass=DeclarativeSubBlocksMetaclass): ...

class StreamValue(MutableSequence):
    """
    Custom type used to represent the value of a StreamBlock; behaves as a sequence of BoundBlocks
    (which keep track of block types in a way that the values alone wouldn't).
    """
    class StreamChild(BoundBlock):
        """
        Iterating over (or indexing into) a StreamValue returns instances of StreamChild.
        These are wrappers for the individual data items in the stream, extending BoundBlock
        (which keeps track of the data item's corresponding Block definition object, and provides
        the `render` method to render itself with a template) with an `id` property (a UUID
        assigned to the item - this is managed by the enclosing StreamBlock and is not a property
        of blocks in general) and a `block_type` property.
        """
        id: Incomplete
        def __init__(self, *args, **kwargs) -> None: ...
        @property
        def block_type(self):
            '''
            Syntactic sugar so that we can say child.block_type instead of child.block.name.
            (This doesn\'t belong on BoundBlock itself because the idea of block.name denoting
            the child\'s "type" (\'heading\', \'paragraph\' etc) is unique to StreamBlock, and in the
            wider context people are liable to confuse it with the block class (CharBlock etc).
            '''
        def get_prep_value(self): ...
    class RawDataView(MutableSequence):
        """
        Internal helper class to present the stream data in raw JSONish format. For backwards
        compatibility with old code that manipulated StreamValue.stream_data, this is considered
        mutable to some extent, with the proviso that once the BoundBlock representation has been
        accessed, any changes to fields within raw data will not propagate back to the BoundBlock
        and will not be saved back when calling get_prep_value.
        """
        stream_value: Incomplete
        def __init__(self, stream_value) -> None: ...
        def __getitem__(self, i): ...
        def __len__(self) -> int: ...
        def __setitem__(self, i, item) -> None: ...
        def __delitem__(self, i) -> None: ...
        def insert(self, i, item) -> None: ...
    class BlockNameLookup(Mapping):
        """
        Dict-like object returned from `blocks_by_name`, for looking up a stream's blocks by name.
        Uses lazy evaluation on access, so that we're not redundantly constructing StreamChild
        instances for blocks of different names.
        """
        stream_value: Incomplete
        block_names: Incomplete
        find_all: Incomplete
        def __init__(self, stream_value, find_all: bool = True) -> None: ...
        def __getitem__(self, block_name): ...
        def __iter__(self): ...
        def __len__(self) -> int: ...
    stream_block: Incomplete
    is_lazy: Incomplete
    raw_text: Incomplete
    def __init__(self, stream_block, stream_data, is_lazy: bool = False, raw_text: Incomplete | None = None) -> None:
        """
        Construct a StreamValue linked to the given StreamBlock,
        with child values given in stream_data.

        Passing is_lazy=True means that stream_data is raw JSONish data as stored
        in the database, and needs to be converted to native values
        (using block.to_python()) when accessed. In this mode, stream_data is a
        list of dicts, each containing 'type' and 'value' keys.

        Passing is_lazy=False means that stream_data consists of immediately usable
        native values. In this mode, stream_data is a list of (type_name, value)
        or (type_name, value, id) tuples.

        raw_text exists solely as a way of representing StreamField content that is
        not valid JSON; this may legitimately occur if an existing text field is
        migrated to a StreamField. In this situation we return a blank StreamValue
        with the raw text accessible under the `raw_text` attribute, so that migration
        code can be rewritten to convert it as desired.
        """
    def __getitem__(self, i): ...
    def __setitem__(self, i, item) -> None: ...
    def __delitem__(self, i) -> None: ...
    def insert(self, i, item) -> None: ...
    @cached_property
    def raw_data(self): ...
    def get_prep_value(self): ...
    def blocks_by_name(self, block_name: Incomplete | None = None): ...
    def first_block_by_name(self, block_name: Incomplete | None = None): ...
    def __eq__(self, other): ...
    def __len__(self) -> int: ...
    def render_as_block(self, context: Incomplete | None = None): ...
    def __html__(self): ...
    def __reduce__(self): ...

class StreamBlockAdapter(Adapter):
    js_constructor: str
    def js_args(self, block): ...
    @cached_property
    def media(self): ...
