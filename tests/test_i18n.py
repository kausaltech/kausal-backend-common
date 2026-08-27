from __future__ import annotations

from pydantic import ConfigDict, PrivateAttr

import pytest

from kausal_common.i18n import helpers
from kausal_common.i18n.pydantic import I18nBaseModel, TranslatedString, set_i18n_context

# FIXME: This is useless for these tests, but is needed for the moment so that these tests can be run in Paths environment
pytestmark = pytest.mark.django_db


class CopyModel(I18nBaseModel):
    label: TranslatedString
    description: TranslatedString
    count: int
    _state: list[str] = PrivateAttr(default_factory=list)


class FrozenCopyModel(CopyModel):
    model_config = ConfigDict(frozen=True)


@pytest.mark.parametrize('model_class', [CopyModel, FrozenCopyModel])
def test_model_copy_normalizes_only_updated_i18n_fields(model_class):
    with set_i18n_context('en', ['de']):
        original = model_class(label='Original', description='Untouched', count=1)
        copied = original.model_copy(update={'label': {'en': 'Updated', 'de': 'Aktualisiert'}, 'count': 'trusted'})

    assert copied.label.i18n == {'en': 'Updated', 'de': 'Aktualisiert'}
    assert copied.description is original.description
    assert copied.count == 'trusted'
    assert original.label.i18n == {'en': 'Original'}
    assert original.count == 1


def test_model_copy_preserves_deep_copy_and_private_attribute_semantics():
    with set_i18n_context('en', []):
        original = FrozenCopyModel(label='Original', description='Untouched', count=1)
    original._state.append('private')

    copied = original.model_copy(update={'label': 'Updated'}, deep=True)

    assert copied.label.i18n == {'en': 'Updated'}
    assert copied._state == ['private']
    assert copied._state is not original._state


def test_model_copy_accepts_language_suffixed_i18n_updates():
    with set_i18n_context('en', ['de']):
        original = FrozenCopyModel(label='Original', description='Untouched', count=1)
        copied = original.model_copy(update={'label_en': 'Updated', 'label_de': 'Aktualisiert'})

    assert copied.label.i18n == {'en': 'Updated', 'de': 'Aktualisiert'}
    assert not hasattr(copied, 'label_en')


@pytest.mark.parametrize(
    ('language_code', 'is_valid'),
    [
        ('', False),
        ('fin', False),
        ('eng-us', False),
        ('en-usa', False),
        ('en--us', False),
        ('en-_us', False),
        ('en-u', False),
        ('enus', False),
        ('en', True),
        ('EN', True),
        ('en-us', True),
        ('en-US', True),
        ('en_us', True),
        ('en_US', True),
        ('EN-us', True),
        ('EN-US', True),
        ('EN_us', True),
        ('EN_US', True),
        ('mww', True),
        ('MWW', True),
    ],
)
def test_convert_language_code_input_validation(language_code, is_valid):
    """Test that trying to convert invalid language code raises an error."""
    if is_valid:
        # Valid codes simply pass
        helpers.convert_language_code(language_code, 'kausal')
    else:
        # Invalid codes raise an error
        with pytest.raises(ValueError, match=f"'{language_code}' is not a valid language code."):
            helpers.convert_language_code(language_code, 'kausal')


@pytest.mark.parametrize(
    ('output_format', 'is_valid'),
    [
        ('', False),
        ('invalid', False),
        ('kausal', True),
        ('django', True),
        ('modeltrans', True),
        ('next.js', True),
        ('wagtail', True),
        ('weblate', True),
    ],
)
def test_convert_language_code_format_validation(output_format, is_valid):
    """Test that trying to convert a language code to an invalid language code format raises an error."""
    if is_valid:
        # Valid formats simply pass
        helpers.convert_language_code('en', output_format)
    else:
        # Invalid formats raise an error
        with pytest.raises(ValueError, match=f"'{output_format}' is not a valid language code format. Valid formats are"):
            helpers.convert_language_code('en', output_format)


@pytest.mark.parametrize(
    ('language_code', 'output_format', 'wanted_result'),
    [
        ('EN', 'kausal', 'en'),
        ('EN_us', 'kausal', 'en-US'),
        ('FI', 'django', 'fi'),
        ('FI_SV', 'django', 'fi-sv'),
        ('FI', 'modeltrans', 'fi'),
        ('FI-SV', 'modeltrans', 'fi_sv'),
        ('EN', 'next.js', 'en'),
        ('EN_us', 'next.js', 'en-US'),
        ('EN', 'wagtail', 'en'),
        ('EN_us', 'wagtail', 'en-US'),
        ('mww', 'kausal', 'mww'),
        ('MWW', 'django', 'mww'),
        ('MWW', 'modeltrans', 'mww'),
        # Weblate spells a locale the way a POSIX locale directory does, which is what its
        # `language_code_style = 'linux'` expects of a filename.
        ('en', 'weblate', 'en'),
        ('EN', 'weblate', 'en'),
        ('es-us', 'weblate', 'es_US'),
        ('es_US', 'weblate', 'es_US'),
        ('sv-fi', 'weblate', 'sv_FI'),
        ('de-CH', 'weblate', 'de_CH'),
        ('MWW', 'weblate', 'mww'),
    ],
)
def test_convert_language_code(language_code, output_format, wanted_result):
    """Test converting language code to wanted format."""
    result = helpers.convert_language_code(language_code, output_format)
    assert result == wanted_result
