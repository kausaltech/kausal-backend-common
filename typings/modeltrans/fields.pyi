from collections.abc import Generator
from typing import Literal, Self, Sequence

from django.db.models import Field, JSONField

class TranslatedVirtualField(Field):
    original_field: Field
    language: str | None
    default_language_field: str | None
    blank: bool
    null: bool
    serialize: bool
    concrete: Literal[False]


class TranslationField(JSONField):
    description: str
    fields: Sequence[str]
    default_language_field: str | None

    @classmethod
    def __new__(
        cls,
        fields: Sequence[str] | None = ...,
        default_language_field: str | None = ...,
        required_languages: list[str] | dict | None = ...,
        virtual_fields: bool = ...,
        fallback_language_field: str | None = ...,
        *args, **kwargs,
    ) -> Self: ...

    def __init__(
        self,
        fields: Sequence[str] | None = ...,
        default_language_field: str | None = ...,
        required_languages: list[str] | dict | None = ...,
        virtual_fields: bool = ...,
        fallback_language_field: str | None = ...,
        *args, **kwargs,
    ) -> None: ...
    def get_translated_fields(self) -> Generator[TranslatedVirtualField, None, None]: ...
