from __future__ import annotations

import importlib
import sysconfig
from importlib.util import find_spec
from typing import TYPE_CHECKING

from django.apps import AppConfig
from django.core.checks import Critical, Warning as CheckWarning, register as register_check

import rich
from loguru import logger
from rich.traceback import Traceback

from kausal_common.context import get_django_project_name

if TYPE_CHECKING:
    from collections.abc import Sequence

    from django.core.checks import CheckMessage


site_packages_path = sysconfig.get_path('purelib')


@register_check
def check_graphql_schema(app_configs, **_kwargs) -> list[CheckMessage]:  # pyright: ignore[reportUnusedParameter]
    project_name = get_django_project_name()
    mod_path = f'{project_name}.schema'
    try:
        importlib.import_module(mod_path)
    except Exception as exc:
        from django.conf import settings

        if settings.DEBUG:
            console = rich.get_console()
            tbp = Traceback.from_exception(type(exc), exc, traceback=exc.__traceback__, max_frames=20, show_locals=True)
            console.print(tbp)
        else:
            logger.exception('GraphQL schema failed to initialize')
        return [Critical('GraphQL schema failed to initialize', id='kausal_common.G001', obj=mod_path)]
    return []


@register_check
def check_roles(app_configs: Sequence[AppConfig] | None, **_kwargs) -> list[CheckMessage]:
    from django.apps import apps

    from kausal_common.models.roles import Role

    app_list = app_configs or list(apps.get_app_configs())
    errors = []
    for app in app_list:
        if app.module is None:
            continue
        roles_mod_name = app.module.__name__ + '.roles'
        spec = find_spec(roles_mod_name)
        if spec is None:
            continue
        roles = importlib.import_module(roles_mod_name)
        for obj in roles.__dict__.values():
            if not isinstance(obj, Role):
                continue
            errors.extend(obj.check())

    return errors


@register_check
def check_model_ordering(app_configs: Sequence[AppConfig] | None, **_kwargs) -> list[CheckMessage]:  # pyright: ignore[reportUnusedParameter]
    from django.apps import apps
    from wagtail.models import Page

    errors: list[CheckMessage] = []
    for model in apps.get_models():
        if model._meta.ordering:
            continue
        if issubclass(model, Page):
            # Wagtail pages are ordered by path through the Manager
            continue
        if model._meta.app_config.path.startswith(site_packages_path):
            continue
        errors.append(
            CheckWarning(
                'Model has no default ordering',
                # hint='Add ordering to the model Meta, e.g., ordering = ("id",)',
                id='kausal_common.M001',
                obj=model,
            )
        )
    return errors


class KausalCommonConfig(AppConfig):
    name = 'kausal_common'

    def ready(self) -> None:
        from kausal_common.development.monkey import monkeypatch_generic_support

        monkeypatch_generic_support()
        return super().ready()
