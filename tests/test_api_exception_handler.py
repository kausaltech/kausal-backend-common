from __future__ import annotations

from django.core.exceptions import ValidationError as DjangoValidationError

from kausal_common.api.exceptions import api_exception_handler


def test_django_validation_error_becomes_400() -> None:
    resp = api_exception_handler(DjangoValidationError({'description': ['bad markup']}), {})
    assert resp is not None
    assert resp.status_code == 400
    assert 'description' in resp.data


def test_plain_django_validation_message_becomes_400() -> None:
    resp = api_exception_handler(DjangoValidationError('just bad'), {})
    assert resp is not None
    assert resp.status_code == 400


def test_non_validation_error_is_left_to_default_handler() -> None:
    # A non-DRF, non-Django-validation error is not handled here (returns None, i.e. 500).
    assert api_exception_handler(RuntimeError('boom'), {}) is None
