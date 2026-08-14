from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

import strawberry as sb

from kausal_common.models.permissions import (
    PermissionedModel,
    UserPermissions,
    get_user_permissions_for_instance,
)
from kausal_common.strawberry.context import GraphQLContext
from kausal_common.strawberry.pydantic import StrawberryPydanticType, pydantic_type

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


@pydantic_type(UserPermissions, name='UserPermissions', all_fields=True)
class UserPermissionsType(StrawberryPydanticType[UserPermissions]):
    pass


def _permissioned_model_from_root(root: Any) -> PermissionedModel | None:
    if isinstance(root, PermissionedModel):
        return root
    model = getattr(root, '_model', None)
    if isinstance(model, PermissionedModel):
        return model
    model = getattr(root, 'db_obj', None)
    if isinstance(model, PermissionedModel):
        return model
    return None


@sb.type
class UserPermissionsMixin:
    """Add effective per-object permissions to a Strawberry model type."""

    @sb.field
    @staticmethod
    def user_permissions(root: Any, info: sb.Info[GraphQLContext, None]) -> UserPermissionsType | None:
        model = _permissioned_model_from_root(root)
        if model is None:
            return None
        permissions = get_user_permissions_for_instance(info.context.get_user(), model)
        return UserPermissionsType.from_pydantic(permissions)
