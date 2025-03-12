from __future__ import annotations

from typing import Any, TypeVar

from django.core.validators import RegexValidator
from django.db import models
from django.utils.translation import gettext_lazy as _


class IdentifierValidator(RegexValidator):
    regex = r'^[a-z0-9-_]+$'


class InstanceIdentifierValidator(RegexValidator):
    regex = r'^[a-z0-9-]+$'


_ST = TypeVar('_ST', bound=Any | None, default=str)
_GT = TypeVar('_GT', bound=Any | None, default=str)

class IdentifierField(models.CharField[_ST, _GT]):
    def __init__(self, *args, **kwargs):
        validator_kwargs = {}
        if 'regex' in kwargs:
            validator_kwargs['regex'] = kwargs.pop('regex')
        if 'validators' not in kwargs:
            kwargs['validators'] = [IdentifierValidator(**validator_kwargs)]
        if 'max_length' not in kwargs:
            kwargs['max_length'] = 50
        if 'verbose_name' not in kwargs:
            kwargs['verbose_name'] = _('identifier')
        super().__init__(*args, **kwargs)
