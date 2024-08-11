from collections.abc import Generator
from typing import Any, Literal, Self, Sequence

from _typeshed import Incomplete
from django.db import models
from wagtail.blocks import Block as Block, BlockField as BlockField, StreamBlock as StreamBlock, StreamValue as StreamValue
from wagtail.rich_text import (
    RichTextMaxLengthValidator as RichTextMaxLengthValidator,
    extract_references_from_rich_text as extract_references_from_rich_text,
    get_text_for_indexing as get_text_for_indexing,
)

class RichTextField(models.TextField):
    editor: str
    features: Sequence[str] | None

    @classmethod
    def __new__(cls, *args, editor: str | None = None, features: Sequence[str] | None = None, **kwargs) -> Self: ...

    def __init__(self, *args, editor: str | None = None, features: Sequence[str] | None = None, **kwargs) -> None: ...

    def clone(self): ...
    def get_searchable_content(self, value): ...
    def extract_references(self, value) -> Generator[Incomplete, Incomplete, None]: ...


type StreamFieldNamedBlock = tuple[str, Block]
type StreamFieldBlocks = Block | type[Block] | Sequence[StreamFieldNamedBlock]

class StreamField(models.Field):
    stream_block: Block

    @classmethod
    def __new__(
        cls,
        block_types: StreamFieldBlocks,
        use_json_field: bool = True,
        min_num: int | None = None,
        max_num: int | None = None,
        block_counts: dict[str, dict[str, int]] | None = None,
        **kwargs,
    ) -> Self: ...

    def __init__(
        self,
        block_types: StreamFieldBlocks,
        use_json_field: bool = True,
        min_num: int | None = None,
        max_num: int | None = None,
        block_counts: dict[str, dict[str, int]] | None = None,
        **kwargs,
    ) -> None: ...
    @property
    def json_field(self) -> models.JSONField: ...
    def get_internal_type(self) -> Literal['JSONField']: ...
    def to_python(self, value) -> StreamValue: ...
    def get_prep_value(self, value: StreamValue) -> Any: ...  # noqa: ANN401
    def value_to_string(self, obj): ...
    def get_searchable_content(self, value): ...
    def extract_references(self, value) -> Any: ...  # noqa: ANN401
    def get_block_by_content_path(self, value, path_elements):
        """
        Given a list of elements from a content path, retrieve the block at that path
        as a BoundBlock object, or None if the path does not correspond to a valid block.
        """  # noqa: D205, PYI021
