from collections.abc import Generator
from typing import Any, Generic, Literal, Self, Sequence
from typing_extensions import TypeVar

from django.db import models
from django.db.models.expressions import Combinable
from wagtail.blocks import Block as Block, BlockField as BlockField, StreamBlock as StreamBlock, StreamValue as StreamValue
from wagtail.rich_text import (
    RichTextMaxLengthValidator as RichTextMaxLengthValidator,
    extract_references_from_rich_text as extract_references_from_rich_text,
    get_text_for_indexing as get_text_for_indexing,
)

from _typeshed import Incomplete

_RTF_ST = TypeVar('_RTF_ST', default=str | Combinable)
_RTF_GT = TypeVar('_RTF_GT', default=str)

class RichTextField(Generic[_RTF_ST, _RTF_GT], models.TextField[_RTF_ST, _RTF_GT]):
    editor: str
    features: Sequence[str] | None

    @classmethod
    def __new__(cls, *args, editor: str | None = None, features: Sequence[str] | None = None, **kwargs) -> Self: ...

    def __init__(self, *args, editor: str | None = None, features: Sequence[str] | None = None, **kwargs) -> None: ...

    def clone(self): ...
    def get_searchable_content(self, value): ...
    def extract_references(self, value) -> Generator[Incomplete, Incomplete, None]: ...


type StreamFieldNamedBlock = tuple[str, Block[Any]]
type StreamFieldBlocks = Block[Any] | type[Block[Any]] | Sequence[StreamFieldNamedBlock]


class StreamField[GT: StreamValue | None = StreamValue](models.Field[Any, GT]):
    stream_block: StreamBlock

    @classmethod
    def __new__(
        cls,
        block_types: StreamFieldBlocks,
        use_json_field: bool = True,
        min_num: int | None = None,
        max_num: int | None = None,
        block_counts: dict[str, dict[str, int]] | None = None,
        blank: bool = False,
        null: bool = False,
        **kwargs,
    ) -> Self: ...

    def __init__(
        self,
        block_types: StreamFieldBlocks,
        use_json_field: bool = True,
        min_num: int | None = None,
        max_num: int | None = None,
        block_counts: dict[str, dict[str, int]] | None = None,
        blank: bool = False,
        null: bool = False,
        **kwargs,
    ) -> None: ...
    @property
    def json_field(self) -> models.JSONField: ...
    def get_internal_type(self) -> Literal['JSONField']: ...
    def to_python(self, value) -> StreamValue: ...
    def get_prep_value(self, value: StreamValue) -> Any: ...
    def value_to_string(self, obj): ...
    def get_searchable_content(self, value): ...
    def extract_references(self, value) -> Any: ...
    def get_block_by_content_path(self, value, path_elements):
        """
        Given a list of elements from a content path, retrieve the block at that path
        as a BoundBlock object, or None if the path does not correspond to a valid block.
        """
