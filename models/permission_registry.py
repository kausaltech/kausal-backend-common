from __future__ import annotations

from django.apps import apps
from django.core.exceptions import ImproperlyConfigured
from wagtail.permission_policies.base import BasePermissionPolicy
from wagtail.permissions import register_permission_policy


def register_model_permission_policies() -> None:
    """
    Register the permission policy each model declares in `permission_policy()` with Wagtail.

    Models opt out with `register_wagtail_permission_policy = False`. Models whose policy the
    project doesn't configure (`permission_policy()` raises `ImproperlyConfigured`) are skipped.
    """
    for model in apps.get_models():
        get_policy = getattr(model, 'permission_policy', None)
        if not callable(get_policy):
            continue
        if not getattr(model, 'register_wagtail_permission_policy', True):
            continue
        try:
            policy = get_policy()
        except ImproperlyConfigured:
            continue
        if not isinstance(policy, BasePermissionPolicy):
            raise TypeError(f'{model._meta.label}.permission_policy() did not return a permission policy')
        register_permission_policy(model, policy, exact_class=True)
