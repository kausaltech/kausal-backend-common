from __future__ import annotations

from rest_framework import serializers

from kausal_common.api.rich_text import RichTextEditorCompatSerializerMixin

from orgs.models import Organization  # has a core RichTextField: description


class _OrgRichTextSerializer(RichTextEditorCompatSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ['description']


def test_mixin_rejects_irreparable_at_validation_time() -> None:
    s = _OrgRichTextSerializer(data={'description': '<p><em>crossed</p></em>'})
    assert not s.is_valid()  # rejected during is_valid(), before any save()
    assert 'description' in s.errors


def test_mixin_accepts_void_tag_markup() -> None:
    s = _OrgRichTextSerializer(data={'description': '<p>a<br>b</p>'})
    assert s.is_valid(), s.errors


def test_mixin_accepts_empty() -> None:
    s = _OrgRichTextSerializer(data={'description': ''})
    assert s.is_valid(), s.errors
