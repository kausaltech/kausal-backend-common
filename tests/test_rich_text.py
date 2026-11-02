from __future__ import annotations

from django.core.exceptions import ValidationError
from wagtail.fields import RichTextField

import pytest

from kausal_common.models.rich_text import make_editor_compatible, normalize_void_tags


@pytest.fixture
def rich_text_field() -> RichTextField:
    field = RichTextField()
    field.set_attributes_from_name('description')
    return field


class TestNormalizeVoidTags:
    @pytest.mark.parametrize(
        ('raw', 'expected'),
        [
            ('<p>a<br>b</p>', '<p>a<br/>b</p>'),
            ('<br>', '<br/>'),
            # Already self-closed tags are left byte-for-byte untouched: the editor parses
            # them fine, so rewriting them (e.g. dropping the space in `<br />`) is needless churn.
            ('<br/>', '<br/>'),
            ('<br />', '<br />'),
            ('<br  />', '<br  />'),
            ('<BR>', '<br/>'),
            ('<img src="x">', '<img src="x"/>'),
            ('<img src="x"/>', '<img src="x"/>'),
            ('<img src="x" />', '<img src="x" />'),
            ('<hr>', '<hr/>'),
            ('plain text', 'plain text'),
            ('<p>no voids</p>', '<p>no voids</p>'),
        ],
    )
    def test_normalizes(self, raw: str, expected: str) -> None:
        assert normalize_void_tags(raw) == expected

    def test_idempotent(self) -> None:
        once = normalize_void_tags('<p>a<br>b<img src="y"></p>')
        assert normalize_void_tags(once) == once


@pytest.mark.django_db
class TestMakeEditorCompatible:
    def test_normalizes_bare_br(self, rich_text_field: RichTextField) -> None:
        assert make_editor_compatible('<p>a<br>b</p>', rich_text_field) == '<p>a<br/>b</p>'

    def test_valid_markup_unchanged(self, rich_text_field: RichTextField) -> None:
        html = '<p>hello <b>world</b></p>'
        assert make_editor_compatible(html, rich_text_field) == html

    def test_empty_values_passthrough(self, rich_text_field: RichTextField) -> None:
        assert make_editor_compatible('', rich_text_field) == ''
        assert make_editor_compatible(None, rich_text_field) is None

    def test_rejects_unparseable_markup(self, rich_text_field: RichTextField) -> None:
        # Crossed tags cannot be fixed by void-tag normalization, so the editor converter
        # still rejects them.
        with pytest.raises(ValidationError):
            make_editor_compatible('<p><em>text</p></em>', rich_text_field)
