from collections.abc import Generator, Sequence
from typing import Any, Iterable, Mapping, type_check_only

from django.core.files.base import File
from django.core.validators import _ValidatorCallable
from django.db.models.base import Model
from django.forms.fields import (
    BooleanField,
    CharField,
    DateField,
    DecimalField,
    Field,
    FloatField,
    IntegerField,
    RegexField,
    URLField,
)
from django.forms.models import ModelChoiceField
from django.forms.widgets import Media, Widget
from django.utils.choices import _Choices
from django.utils.functional import cached_property
from django_stubs_ext import StrOrPromise
from wagtail.models import Page
from wagtail.rich_text import RichText
from wagtail.telepath import Adapter

from _typeshed import Incomplete

from .base import Block, BlockMeta

__all__ = [
    'BlockQuoteBlock',
    'BooleanBlock',
    'CharBlock',
    'ChoiceBlock',
    'ChooserBlock',
    'DateBlock',
    'DateTimeBlock',
    'DecimalBlock',
    'EmailBlock',
    'FieldBlock',
    'FloatBlock',
    'IntegerBlock',
    'MultipleChoiceBlock',
    'PageChooserBlock',
    'RawHTMLBlock',
    'RegexBlock',
    'RichTextBlock',
    'TextBlock',
    'TimeBlock',
    'URLBlock',
]

@type_check_only
class FieldBlockMeta(BlockMeta):
    default: Any

class FieldBlock[F: Field](Block[FieldBlockMeta]):
    """A block that wraps a Django form field"""

    @property
    def field(self) -> F: ...
    field_options: dict[str, Any]

    def id_for_label(self, prefix: str) -> str: ...
    def value_from_form(self, value):
        """
        The value that we get back from the form field might not be the type
        that this block works with natively; for example, the block may want to
        wrap a simple value such as a string in an object that provides a fancy
        HTML rendering (e.g. EmbedBlock).

        We therefore provide this method to perform any necessary conversion
        from the form field value to the block's native value. As standard,
        this returns the form field value unchanged.
        """
    def value_for_form(self, value):
        """
        Reverse of value_from_form; convert a value of this block's native value type
        to one that can be rendered by the form field
        """
    def value_from_datadict(self, data: Mapping[str, Any], files: Mapping[str, Iterable[File]], prefix: str) -> None: ...
    def value_omitted_from_data(self, data: Mapping[str, Any], files: Mapping[str, Iterable[File]], prefix: str) -> bool: ...
    def clean(self, value): ...
    @property
    def required(self): ...
    def get_form_state(self, value): ...


class FieldBlockAdapter(Adapter):
    js_constructor: str
    def js_args(self, block: FieldBlock[Any]) -> list: ...
    @cached_property
    def media(self) -> Media: ...

class CharBlock(FieldBlock[CharField]):
    search_index: bool
    def __init__(
        self,
        required: bool = True,
        help_text: StrOrPromise | None = None,
        max_length: int | None = None,
        min_length: int | None = None,
        validators: Sequence[_ValidatorCallable] = (),
        search_index: bool = True,
        **kwargs,
    ) -> None: ...
    def get_searchable_content(self, value: str) -> list[str]: ...

class TextBlock(FieldBlock[CharField]):
    field_options: Incomplete
    rows: Incomplete
    search_index: Incomplete
    def __init__(
        self,
        required: bool = True,
        help_text: StrOrPromise | None = None,
        rows: int = 1,
        max_length: int | None = None,
        min_length: int | None = None,
        search_index: bool = True,
        validators: Sequence[_ValidatorCallable] = (),
        **kwargs,
    ) -> None: ...

    @property
    def field(self) -> CharField: ...

    def get_searchable_content(self, value: str) -> list[str]: ...
    Meta: type[Any]

class BlockQuoteBlock(TextBlock):
    def render_basic(self, value, context: Incomplete | None = None): ...
    class Meta:
        icon: str

class FloatBlock(FieldBlock[FloatField]):
    def __init__(
        self,
        required: bool = True,
        max_value: float | None = None,
        min_value: float | None = None,
        validators: Sequence[_ValidatorCallable] = (),
        *args,
        **kwargs,
    ) -> None: ...
    class Meta:
        icon: str

class DecimalBlock(FieldBlock[DecimalField]):
    def __init__(
        self,
        required: bool = True,
        help_text: StrOrPromise | None = None,
        max_value: Incomplete | None = None,
        min_value: Incomplete | None = None,
        max_digits: Incomplete | None = None,
        decimal_places: Incomplete | None = None,
        validators: Sequence[_ValidatorCallable] = (),
        *args,
        **kwargs,
    ) -> None: ...
    def to_python(self, value): ...
    class Meta:
        icon: str

class RegexBlock(FieldBlock[RegexField]):
    def __init__(
        self,
        regex,
        required: bool = True,
        help_text: StrOrPromise | None = None,
        max_length: int | None = None,
        min_length: int | None = None,
        error_messages: Incomplete | None = None,
        validators: Sequence[_ValidatorCallable] = (),
        *args,
        **kwargs,
    ) -> None: ...
    class Meta:
        icon: str

class URLBlock(FieldBlock[URLField]):
    def __init__(
        self,
        required: bool = True,
        help_text: StrOrPromise | None = None,
        max_length: int | None = None,
        min_length: int | None = None,
        validators: Sequence[_ValidatorCallable] = (),
        **kwargs,
    ) -> None: ...
    class Meta:
        icon: str

class BooleanBlock(FieldBlock[BooleanField]):
    def __init__(self, required: bool = True, help_text: StrOrPromise | None = None, **kwargs) -> None: ...
    def get_form_state(self, value): ...
    class Meta:
        icon: str

class DateBlock(FieldBlock[DateField]):
    field_options: Incomplete
    format: str
    def __init__(
        self,
        required: bool = True,
        help_text: StrOrPromise | None = None,
        format: str | None = None,
        validators: Sequence[_ValidatorCallable] = (),
        **kwargs,
    ) -> None: ...
    @cached_property
    def field(self): ...
    def to_python(self, value): ...
    class Meta:
        icon: str

class TimeBlock(FieldBlock):
    field_options: Incomplete
    format: str
    def __init__(
        self,
        required: bool = True,
        help_text: StrOrPromise | None = None,
        format: str | None = None,
        validators: Sequence[_ValidatorCallable] = (),
        **kwargs,
    ) -> None: ...
    @cached_property
    def field(self): ...
    def to_python(self, value): ...
    class Meta:
        icon: str

class DateTimeBlock(FieldBlock):
    field_options: Incomplete
    format: str
    def __init__(
        self,
        required: bool = True,
        help_text: StrOrPromise | None = None,
        format: str | None = None,
        validators: Sequence[_ValidatorCallable] = (),
        **kwargs,
    ) -> None: ...
    @cached_property
    def field(self): ...
    def to_python(self, value): ...
    class Meta:
        icon: str

class EmailBlock(FieldBlock):
    field: Incomplete
    def __init__(self, required: bool = True, help_text: Incomplete | None = None, validators=(), **kwargs) -> None: ...
    class Meta:
        icon: str

class IntegerBlock(FieldBlock[IntegerField]):
    field: Incomplete
    def __init__(
        self,
        required: bool = True,
        help_text: StrOrPromise | None = None,
        min_value: int | None = None,
        max_value: int | None = None,
        validators=(),
        **kwargs,
    ) -> None: ...

    class Meta:
        icon: str

class BaseChoiceBlock(FieldBlock):
    choices: _Choices
    search_index: bool
    field: Incomplete
    def __init__(
        self,
        choices: _Choices | None = None,
        default: Incomplete | None = None,
        required: bool = True,
        help_text: StrOrPromise | None = None,
        search_index: bool = True,
        widget: Widget | type[Widget] | None = None,
        validators: Sequence[_ValidatorCallable] = (),
        **kwargs,
    ) -> None: ...
    class Meta:
        icon: str

class ChoiceBlock(BaseChoiceBlock):
    def get_field(self, **kwargs): ...
    def deconstruct(self):
        """
        Always deconstruct ChoiceBlock instances as if they were plain ChoiceBlocks with their
        choice list passed in the constructor, even if they are actually subclasses. This allows
        users to define subclasses of ChoiceBlock in their models.py, with specific choice lists
        passed in, without references to those classes ending up frozen into migrations.
        """
    def get_searchable_content(self, value): ...

class MultipleChoiceBlock(BaseChoiceBlock):
    def get_field(self, **kwargs): ...
    def deconstruct(self):
        """
        Always deconstruct MultipleChoiceBlock instances as if they were plain
        MultipleChoiceBlocks with their choice list passed in the constructor,
        even if they are actually subclasses. This allows users to define
        subclasses of MultipleChoiceBlock in their models.py, with specific choice
        lists passed in, without references to those classes ending up frozen
        into migrations.
        """
    def get_searchable_content(self, value): ...

class RichTextBlock(FieldBlock):
    field_options: Incomplete
    max_length: Incomplete
    editor: str
    features: Sequence[str] | None
    search_index: bool
    def __init__(
        self,
        required: bool = True,
        help_text: StrOrPromise | None = None,
        editor: str = 'default',
        features: Sequence[str] | None = None,
        max_length: int | None = None,
        validators=(),
        search_index: bool = True,
        **kwargs,
    ) -> None: ...
    def to_python(self, value) -> RichText: ...
    def get_prep_value(self, value: RichText) -> str: ...
    def normalize(self, value: RichText | str) -> RichText: ...
    @cached_property
    def field(self) -> CharField: ...
    def value_for_form(self, value: RichText) -> str: ...
    def value_from_form(self, value: str) -> RichText: ...
    def get_searchable_content(self, value) -> list[str]: ...
    def extract_references(self, value) -> Generator[Incomplete, Incomplete]: ...
    class Meta:
        icon: str


class RawHTMLBlock(FieldBlock):
    field: Incomplete
    def __init__(self, required: bool = True, help_text: Incomplete | None = None, max_length: Incomplete | None = None, min_length: Incomplete | None = None, validators=(), **kwargs) -> None: ...
    def get_default(self): ...
    def to_python(self, value): ...
    def normalize(self, value): ...
    def get_prep_value(self, value): ...
    def value_for_form(self, value): ...
    def value_from_form(self, value): ...
    class Meta:
        icon: str

class ChooserBlock[M: Model](FieldBlock[ModelChoiceField[M]]):
    def __init__(
        self,
        required: bool = True,
        help_text: StrOrPromise | None = None,
        validators: Sequence[_ValidatorCallable] = (),
        **kwargs,
    ) -> None: ...
    @cached_property
    def model_class(self) -> type[M]: ...
    @cached_property
    def field(self) -> ModelChoiceField[M]: ...
    def to_python(self, value) -> M | None: ...
    def bulk_to_python(self, values) -> list[M | None]:
        """
        Return the model instances for the given list of primary keys.

        The instances must be returned in the same order as the values and keep None values.
        """
    def get_prep_value(self, value: M | None) -> int | None: ...
    def value_from_form(self, value: int | M) -> M | None: ...
    def get_form_state(self, value: M | None) -> dict[str, Any]: ...
    def clean(self, value: M | None) -> M | None: ...
    def extract_references(self, value) -> Generator[Incomplete]: ...
    class Meta:
        icon: str

class PageChooserBlock(ChooserBlock):
    page_type: Incomplete
    can_choose_root: Incomplete
    def __init__(
        self,
        page_type: Sequence[type[Page] | str] | None = None,
        can_choose_root: bool = False,
        target_model: type[Page] | None = None,
        **kwargs,
    ) -> None: ...
    @cached_property
    def target_model(self) -> type[Page]:
        """
        Defines the model used by the base ChooserBlock for ID <-> instance
        conversions. If a single page type is specified in target_model,
        we can use that to get the more specific instance "for free"; otherwise
        use the generic Page model.
        """
    @cached_property
    def target_models(self): ...
    @cached_property
    def widget(self): ...
    def get_form_state(self, value): ...
    def render_basic(self, value, context: Incomplete | None = None): ...
    def deconstruct(self): ...
    class Meta:
        icon: str
