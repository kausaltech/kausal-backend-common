from __future__ import annotations

import importlib
import typing

from django.core.exceptions import ImproperlyConfigured

from kausal_common.models.permissions import PermissionedModel

from .config import dataset_config

if typing.TYPE_CHECKING:
    from kausal_common.models.permission_policy import ModelPermissionPolicy
    from kausal_common.models.types import QS


def get_permission_policy[_M: PermissionedModel](key: str) -> ModelPermissionPolicy[_M, QS[_M]]:
    if not hasattr(dataset_config, key):
        raise ImproperlyConfigured(
            f'{key} is required in the settings to use the datasets app.'
        )
    permission_policy_class_name: str = getattr(dataset_config, key)
    parts = permission_policy_class_name.split('.')
    module_name = '.'.join(parts[0:-1])
    class_name = parts[-1]
    permission_policy_module = importlib.import_module(module_name)
    permission_policy_class = getattr(permission_policy_module, class_name)
    return permission_policy_class()
