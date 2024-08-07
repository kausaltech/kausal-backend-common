from __future__ import annotations

from typing import TYPE_CHECKING

from django.conf import settings
from modeltrans.translator import get_i18n_field
from modeltrans.utils import get_instance_field_value

if TYPE_CHECKING:
    from django.db import models
    from modeltrans.fields import TranslationField


def get_language_from_default_language_field(
    instance: models.Model,
    i18n_field: TranslationField | None = None,
):
    """Return the primary language from the default language field"""
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
