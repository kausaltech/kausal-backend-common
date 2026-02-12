from typing import Any

from django.contrib.auth.models import AbstractBaseUser
from django.db.models import Model
from wagtail.permission_policies.base import BasePermissionPolicy

class ModelAdminURLFinder[M: Model]:
    """
    Handles admin edit URL lookups for an individual model
    """
    edit_url_name: str
    permission_policy: BasePermissionPolicy[Any, Any, Any] = ...
    def __init__(self, user: AbstractBaseUser | None = None) -> None:
        ...

    def construct_edit_url(self, instance: M) -> str:
        """
        Return the edit URL for the given instance - regardless of whether the user can access it -
        or None if no edit URL is available.
        """

    def get_edit_url(self, instance: M) -> str | None:
        """
        Return the edit URL for the given instance if one exists and the user has permission for it,
        or None otherwise.
        """



class NullAdminURLFinder:
    """
    A dummy AdminURLFinder that always returns None
    """
    def __init__(self, user=...) -> None:
        ...

    def get_edit_url(self, instance) -> None:
        ...



finder_classes = ...
def register_admin_url_finder(model: type[Model], handler) -> None:
    ...

class AdminURLFinder:
    """
    The 'main' admin URL finder, which searches across all registered models
    """
    def __init__(self, user=...) -> None:
        ...

    def get_edit_url(self, instance) -> None:
        ...
