from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from wagtail.fields import RichTextField

from kausal_common.models.rich_text import make_editor_compatible

if TYPE_CHECKING:
    from django.db.models import Model


class RichTextEditorCompatSerializerMixin:
    """
    Reject rich-text field values the Draftail editor cannot read back, with a per-field 400.

    Add this to a ``ModelSerializer`` whose model has one or more ``RichTextField``s. The check
    runs in ``validate()`` -- before ``save()`` -- so genuinely unparseable markup fails fast
    with a field-keyed 400 instead of tripping the model-layer guard (``RichTextEditorCompatible
    Mixin``) during save and surfacing as a 500. Markup that only needs void-tag normalization
    passes and is normalized on save. Every core ``RichTextField`` on the model is covered.

    Serializers that define their own ``validate()`` keep working as long as they call
    ``super().validate(data)``.
    """

    def validate(self, data: dict[str, Any]) -> dict[str, Any]:
        data = super().validate(data)  # type: ignore[misc]
        model: type[Model] = self.Meta.model  # type: ignore[attr-defined]
        errors: dict[str, list[str]] = {}
        for field in model._meta.concrete_fields:
            if not isinstance(field, RichTextField):
                continue
            value = data.get(field.name)
            if not value:
                continue
            try:
                make_editor_compatible(value, field)
            except DjangoValidationError as exc:
                errors[field.name] = list(exc.messages)
        if errors:
            raise serializers.ValidationError(errors)
        return data
