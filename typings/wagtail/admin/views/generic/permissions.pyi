from typing import Any, Iterable

from wagtail.permission_policies import BasePermissionPolicy

class PermissionCheckedMixin:
    permission_required: str | None
    any_permission_required: Iterable[str] | None

    @property
    def permission_policy(self) -> BasePermissionPolicy[Any, Any, Any]: ...

    def user_has_permission(self, permission: str) -> bool: ...
    def user_has_any_permission(self, permissions: Iterable[str]) -> bool: ...
