from __future__ import annotations

import re
import threading
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _, override
from wagtail.fields import RichTextField

if TYPE_CHECKING:
    from collections.abc import Iterator

    from wagtail.admin.rich_text.converters.contentstate import ContentstateConverter

# HTML void elements have no end tag. Wagtail's html_to_contentstate converter is built on
# Python's HTMLParser and pushes every start tag onto an open-element stack, so a bare (not
# self-closed) void tag such as `<br>` is never popped and makes the editor read path crash
# with `AssertionError: Unmatched tags: ...`. Draftail always emits self-closed void tags;
# values written as raw HTML through the API/MCP do not, so we normalize them here.
_VOID_ELEMENTS = 'area|base|br|col|embed|hr|img|input|keygen|link|meta|param|source|track|wbr'
_VOID_TAG_RE = re.compile(rf'<({_VOID_ELEMENTS})\b([^>]*)>', re.IGNORECASE)
_VOID_HINT_RE = re.compile(rf'<(?:{_VOID_ELEMENTS})\b', re.IGNORECASE)

_converter_cache: dict[tuple[str, tuple[str, ...] | None], ContentstateConverter] = {}
_converter_cache_lock = threading.Lock()

_skip_validation = threading.local()


def normalize_void_tags(html: str) -> str:
    """
    Self-close bare HTML void elements (e.g. ``<br>`` -> ``<br/>``).

    Only tags that are *not* already self-closed are rewritten; markup the editor can already
    parse, such as ``<br />`` or ``<img src="x" />``, is left byte-for-byte untouched, since
    rewriting it (e.g. dropping the space) would be needless churn. Idempotent: re-running
    yields the same output. This makes raw HTML (from the API/MCP) readable by the Draftail
    editor, which crashes only on bare, non-self-closed void tags.
    """

    def repl(match: re.Match[str]) -> str:
        attrs = match.group(2)
        if attrs.rstrip().endswith('/'):
            # Already self-closed and editor-readable; leave exactly as-is.
            return match.group(0)
        return f'<{match.group(1).lower()}{attrs}/>'

    return _VOID_TAG_RE.sub(repl, html)


def _converter_for(field: RichTextField) -> ContentstateConverter:
    """
    Return the editor converter for ``field``, cached by its editor and feature set.

    Building the Draftail widget assembles the feature registry, which is the expensive part;
    it must happen once per field configuration, never per value.
    """
    # Imported lazily: wagtail.admin.rich_text pulls in the contentstate converter, which
    # calls swapper.load_model() at import time and so must not run at model-definition time.
    from wagtail.admin.rich_text import get_rich_text_editor_widget
    from wagtail.admin.rich_text.converters.contentstate import ContentstateConverter
    from wagtail.rich_text import features as feature_registry

    features = field.features
    key = (field.editor, tuple(features) if features is not None else None)
    converter = _converter_cache.get(key)
    if converter is not None:
        return converter
    with _converter_cache_lock:
        converter = _converter_cache.get(key)
        if converter is not None:
            return converter
        widget = get_rich_text_editor_widget(field.editor, features=field.features)
        converter = getattr(widget, 'converter', None)
        if converter is None:
            feats = field.features if field.features is not None else feature_registry.get_default_features()
            converter = ContentstateConverter(feats)
        _converter_cache[key] = converter
        return converter


def rich_text_source(value: Any) -> str | None:
    """
    Return the stored DB HTML for a rich-text value.

    Wagtail's native ``RichTextField`` descriptor returns a ``RichText`` wrapper whose
    ``.source`` holds the stored HTML; django-modeltrans-managed fields return a plain str.
    """
    if value is None:
        return None
    source = getattr(value, 'source', value)
    return source if isinstance(source, str) else str(source)


def make_editor_compatible(value: Any, field: RichTextField) -> str | None:
    """
    Return a version of ``value`` the Draftail editor can read back.

    Void tags are self-closed (cheaply, only when present). The result is then validated
    against the editor's own converter; markup that still cannot be parsed (e.g. crossed
    tags) raises ``ValidationError``. Empty/plain values are returned untouched.
    """
    raw = rich_text_source(value)
    if not raw:
        return raw
    cleaned = normalize_void_tags(raw) if _VOID_HINT_RE.search(raw) else raw
    if '<' in cleaned:
        try:
            _converter_for(field).from_database_format(cleaned)
        except ValidationError:
            raise
        except Exception as exc:
            raise ValidationError(
                _('Rich text content is not compatible with the editor: %(reason)s') % {'reason': str(exc)},
            ) from exc
    return cleaned


@contextmanager
def skip_rich_text_validation() -> Iterator[None]:
    """
    Temporarily disable rich-text editor-compatibility checking on model clean()/save().

    For trusted internal bulk pipelines (importers, data migrations) that are known to emit
    editor-safe HTML and run at high volume. The public REST API and the MCP server never
    use this.
    """
    previous = getattr(_skip_validation, 'enabled', False)
    _skip_validation.enabled = True
    try:
        yield
    finally:
        _skip_validation.enabled = previous


def _validation_skipped() -> bool:
    return getattr(_skip_validation, 'enabled', False)


class RichTextEditorCompatibleMixin(models.Model):  # noqa: DJ008
    """
    Keep every ``RichTextField`` value readable by the Draftail editor.

    On clean() (covering ``full_clean()`` paths, e.g. GraphQL mutations) and save() (covering
    bare-save / DRF paths) each rich-text value is normalized (void tags self-closed) and
    validated; anything the editor converter still rejects raises ``ValidationError``.
    Per-language values stored in a django-modeltrans ``i18n`` JSON column are handled too.
    """

    if TYPE_CHECKING:
        Meta: Any
    else:

        class Meta:
            abstract = True

    def save(self, *args: Any, **kwargs: Any) -> None:
        # On a targeted `update_fields` save, only check the rich-text fields actually being
        # written, so unrelated saves (status/order recalcs) never re-validate untouched values.
        update_fields = kwargs.get('update_fields')
        only_fields = set(update_fields) if update_fields is not None else None
        self.clean_rich_text_fields(only_fields=only_fields)
        super().save(*args, **kwargs)

    def clean(self) -> None:
        super().clean()
        self.clean_rich_text_fields()

    def clean_rich_text_fields(self, only_fields: set[str] | None = None) -> None:
        """
        Normalize + validate all rich-text values in place; raise on incompatible markup.

        Pure CPU, no DB access, so it is safe to call from bulk paths that must stay fast.
        ``only_fields`` restricts the check to those field names (plus ``i18n`` translations
        when the field name or ``i18n`` is included); ``None`` checks every rich-text field.
        """
        if _validation_skipped():
            return
        errors: dict[str, Any] = {}
        i18n = getattr(self, 'i18n', None)
        if not isinstance(i18n, dict):
            i18n = None
        for field in self._meta.concrete_fields:
            if isinstance(field, RichTextField):
                self._clean_one_rich_text_field(field, i18n, errors, only_fields)
        if errors:
            raise ValidationError(errors)

    def _clean_one_rich_text_field(
        self,
        field: RichTextField,
        i18n: dict[str, Any] | None,
        errors: dict[str, Any],
        only_fields: set[str] | None = None,
    ) -> None:
        name = field.name
        check_base = only_fields is None or name in only_fields
        check_i18n = only_fields is None or name in only_fields or 'i18n' in only_fields
        # Base value, resolved to the default-language column regardless of the active
        # language (django-modeltrans routes attribute access by active language).
        if check_base:
            with override(None):
                base = getattr(self, name)
                try:
                    cleaned = make_editor_compatible(base, field)
                except ValidationError as exc:
                    errors[name] = exc.messages
                else:
                    if cleaned != rich_text_source(base):
                        setattr(self, name, cleaned)
        if i18n is None or not check_i18n:
            return
        prefix = f'{name}_'
        for key in [k for k in i18n if k.startswith(prefix)]:
            try:
                cleaned = make_editor_compatible(i18n[key], field)
            except ValidationError as exc:
                errors[key] = exc.messages
            else:
                if cleaned != i18n[key]:
                    i18n[key] = cleaned
