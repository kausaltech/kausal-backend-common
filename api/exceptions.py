from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _
from rest_framework import exceptions, status


class ProtectedError(exceptions.APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _('Cannot delete instance because other objects reference it.')
    default_code = 'protected_error'


class HandleProtectedErrorMixin:
    """Mixin for viewsets that use DRF's DestroyModelMixin to handle ProtectedError gracefully."""

    def perform_destroy(self, instance):
        try:
            super().perform_destroy(instance)
        except models.ProtectedError as err:
            raise ProtectedError(
                detail={
                    'non_field_errors': _(
                        'Cannot delete "%s" because it is connected to other objects '
                        'such as instances, persons or actions.',
                    ) % getattr(instance, 'name', str(instance)),
                },
            ) from err

