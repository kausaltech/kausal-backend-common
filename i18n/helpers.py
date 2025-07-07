from __future__ import annotations

import re
from typing import TYPE_CHECKING, Literal

from django.conf import settings

if TYPE_CHECKING:
    from django.db import models
    from modeltrans.fields import TranslationField

LANGUAGE_CODE_REGEXP = re.compile(r'^([a-zA-Z]{2})(?:[_-]{1}([a-zA-Z]{2}))?$')


def get_language_from_default_language_field(
    instance: models.Model,
    i18n_field: TranslationField | None = None,
):
    """Return the primary language from the default language field."""

    from modeltrans.translator import get_i18n_field
    from modeltrans.utils import get_instance_field_value

    if not i18n_field:
        i18n_field = get_i18n_field(instance._meta.model)  # pyright: ignore

    if i18n_field is None:
        raise ValueError('No i18n field found for', instance)

    if i18n_field.default_language_field:
        default_language = get_instance_field_value(instance, i18n_field.default_language_field)
    else:
        default_language = settings.LANGUAGE_CODE
    if isinstance(default_language, str):
        default_language = default_language.lower()
    else:
        raise ValueError('Invalid default_language for', instance, default_language)
    return default_language


def convert_language_code(
    language_code: str,
    output_format: Literal['kausal', 'django', 'modeltrans', 'next.js', 'wagtail'],
) -> str:
    """
    Convert given language code to wanted output format.

    Args:
        language_code (str): The language code to convert.
        output_format (str): The output format to which to convert the language code to. The formats are:
            'kausal': The format to use internally. (e.g. 'es-US')
            'django': The format used by Django, e.g. django.utils.translation.get_language. ('es-us')
            'modeltrans': The format used by django-modeltrans. ('es_us')
            'next.js': The format used by next.js. ('es-US')
            'wagtail': The format used by Wagtail, in particular its Locale objects. ('es-US')

    Returns:
        Given language code converted to wanted format as a string.

    Raises:
        ValueError: If language_code or output_format are invalid.

    """
    regex_match = LANGUAGE_CODE_REGEXP.match(language_code)
    if not regex_match:
        error_message = f"'{language_code}' is not a valid language code."
        raise ValueError(error_message)

    language, region = regex_match.groups()
    match output_format:
        case "kausal" | "next.js" | "wagtail":
            result = language.lower()
            result += f"-{region.upper()}" if region else ""
            return result
        case "django":
            result = language.lower()
            result += f"-{region.lower()}" if region else ""
            return result
        case "modeltrans":
            result = language.lower()
            result += f"_{region.lower()}" if region else ""
            return result
        case _:
            format_options = ["kausal", "django", "modeltrans", "next.js", "wagtail"]
            error_message = f"'{output_format}' is not a valid language code format. Valid formats are {format_options}"
            raise ValueError(error_message)


def get_supported_languages():
    yield from settings.LANGUAGES

def get_default_language():
    """Return the global default language from Django settings."""
    return settings.LANGUAGES[0][0]

def get_default_language_lowercase():
    return get_default_language().lower()
