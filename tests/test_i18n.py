from __future__ import annotations

import pytest

from kausal_common.i18n import helpers

# FIXME: This is useless for these tests, but is needed for the moment so that these tests can be run in Paths environment
pytestmark = pytest.mark.django_db


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
    ],
)
def test_convert_language_code(language_code, output_format, wanted_result):
    """Test converting language code to wanted format."""
    result = helpers.convert_language_code(language_code, output_format)
    assert result == wanted_result
