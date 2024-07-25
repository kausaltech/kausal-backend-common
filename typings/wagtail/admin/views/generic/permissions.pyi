from typing import Iterable, Optional

from wagtail.permission_policies import BasePermissionPolicy

class PermissionCheckedMixin:
    permission_policy: BasePermissionPolicy
    permission_required: Optional[str]
    any_permission_required: Iterable[str] | None

    def dispatch(self, request, *args, **kwargs): ...
    def user_has_permission(self, permission: str): ...
    def user_has_any_permission(self, permissions: Iterable[str]): ...
