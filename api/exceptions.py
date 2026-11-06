from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _
from rest_framework import exceptions, status
from rest_framework.serializers import as_serializer_error
from rest_framework.views import exception_handler as drf_exception_handler

if TYPE_CHECKING:

    class DestroyMixinBase:
        def perform_destroy(self, instance) -> None: ...

else:
    DestroyMixinBase = object


def api_exception_handler(exc: Exception, context: Any):
    """
    DRF exception handler that renders Django's ValidationError as a 400 instead of a 500.

    DRF's default handler leaves ``django.core.exceptions.ValidationError`` uncaught, so model-
    level validation raised from ``save()`` -- e.g. the rich-text editor-compatibility guard in
    ``kausal_common.models.rich_text`` -- surfaces as a 500. Convert it to a DRF
    ``ValidationError`` so the client receives a 400 with the per-field messages. Everything
    else is left to DRF's default handler untouched.
    """
    if isinstance(exc, DjangoValidationError):
        exc = exceptions.ValidationError(detail=as_serializer_error(exc))
    return drf_exception_handler(exc, context)


class ProtectedError(exceptions.APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _('Cannot delete instance because other objects reference it.')
    default_code = 'protected_error'


class HandleProtectedErrorMixin(DestroyMixinBase):
    """Mixin for viewsets that use DRF's DestroyModelMixin to handle ProtectedError gracefully."""

    def perform_destroy(self, instance):
        try:
            super().perform_destroy(instance)
        except models.ProtectedError as err:
            raise ProtectedError(
                detail={
                    'non_field_errors': _(
                        'Cannot delete "%s" because it is connected to other objects such as instances, persons or actions.',
                    )
                    % getattr(instance, 'name', str(instance)),
                },
            ) from err
