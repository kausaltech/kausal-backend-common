from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

import strawberry as sb

if TYPE_CHECKING:
    from collections.abc import Awaitable

    from kausal_common.const import IS_PATHS
    if IS_PATHS:
        from paths import gql
    else:
        from aplans import gql

class BasePermission(sb.BasePermission, ABC):
    @abstractmethod
    def has_permission(self, source: Any, info: gql.Info, **kwargs: Any) -> bool | Awaitable[bool]:
        """
        Check if the permission should be accepted.

        This method should be overridden by the subclasses.
        """
        raise NotImplementedError('Permission classes should override has_permission method')


class SuperuserOnly(BasePermission):
    message = 'You must be a superuser to access this resource.'

    def has_permission(self, source: Any, info: gql.Info, **kwargs: Any) -> bool | Awaitable[bool]:
        user = info.context.get_user()
        if not user.is_authenticated:
            return False
        if not user.is_active:
            return False
        return user.is_superuser
