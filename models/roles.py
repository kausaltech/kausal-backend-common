from __future__ import annotations

import abc
from functools import cache, cached_property
from typing import TYPE_CHECKING, ClassVar, Literal, Protocol

from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.db.models import Model, QuerySet
from wagtail.models import PAGE_PERMISSION_CODENAMES, GroupPagePermission

from loguru import logger

if TYPE_CHECKING:
    from collections.abc import Sequence

    from django.utils.functional import _StrPromise as StrPromise  # type: ignore
    from wagtail.models.sites import Site

    from users.models import User


type ModelActionType = Literal['view', 'change', 'delete', 'add']

ALL_MODEL_PERMS: tuple[ModelActionType, ...] = ('view', 'change', 'delete', 'add')


def _get_perm_objs(model, perms) -> list[Permission]:
    content_type = ContentType.objects.get_for_model(model)
    perms = ['%s_%s' % (x, model._meta.model_name) for x in perms]
    perm_objs = Permission.objects.filter(content_type=content_type, codename__in=perms)
    return list(perm_objs)


type AppModelPerms = dict[str, set[str]]


def model_perm(app_label: str, models: str | Sequence[str], perms: Sequence[str]):
    if isinstance(models, str):
        models = [models]
    return (app_label, ['%s_%s' % (p, m) for p in perms for m in models])

def join_perms(model_perms: list[tuple[str, list[str]]]):
    out: AppModelPerms = {}
    for app_label, perms in model_perms:
        out[app_label] = out.get(app_label, set()).union(set(perms))
    return out


class ConcreteRoleProtocol(Protocol):
    id: ClassVar[str]
    name: StrPromise
    group_name: str


class Role(abc.ABC, ConcreteRoleProtocol):
    page_perms: ClassVar[set[str]] = set()
    model_perms: ClassVar[list[tuple[str, str | Sequence[str], Sequence[str]]]] = []

    @cached_property
    def _app_model_perms(self) -> AppModelPerms:
        perms = [model_perm(app_label, models, perms) for app_label, models, perms in self.model_perms]
        return join_perms(perms)

    @cache  # noqa: B019
    def _get_actions_for_model(self, app_label: str, model_name: str) -> set[str]:
        actions = set[str]()
        for perm_app_label, models, perms in self.model_perms:
            if perm_app_label != app_label:
                continue
            if isinstance(models, str):
                models = [models]  # noqa: PLW2901
            if model_name in models:
                actions.update(perms)
        return actions

    @cached_property
    def perms_by_app(self):
        perms = Permission.objects\
            .filter(content_type__app_label__in=self._app_model_perms.keys())\
            .select_related('content_type')
        by_app: dict[str, dict[str, Permission]] = {}
        for perm in perms:
            ct = perm.content_type
            app_perms = by_app.setdefault(ct.app_label, {})
            app_perms[perm.codename] = perm
        return by_app

    def _update_model_perms(self, group: Group) -> None:
        old_perms = set(group.permissions.all())
        new_perms = set()
        for app_label, perms in self._app_model_perms.items():
            for p in list(perms):
                new_perms.add(self.perms_by_app[app_label][p])

        if old_perms != new_perms:
            logger.info('Permission changes detected in group %s, setting new permissions' % self.group_name)
            group.permissions.set(new_perms)

    def get_actions_for_model(self, model: type[Model]) -> set[str]:
        return self._get_actions_for_model(model._meta.app_label, model._meta.model_name)

    def refresh(self):
        group, _ = Group.objects.get_or_create(name=str(self.name))
        self._update_model_perms(group)


class InstanceSpecificRole[M: Model](Role, abc.ABC):
    model: type[M]

    def __init__(self, model: type[M]):
        self.model = model

    @abc.abstractmethod
    def get_instance_group_name(self, obj: M) -> str: ...

    @abc.abstractmethod
    def update_instance_group(self, obj: M, group: Group): ...

    @abc.abstractmethod
    def get_existing_instance_group(self, obj: M) -> Group | None: ...

    @abc.abstractmethod
    def get_instance_site(self, obj: M) -> Site | None: ...

    @abc.abstractmethod
    def get_instances_for_user(self, user: User) -> QuerySet[M, M]:
        """Return the objects for which the user has this role."""

    def _update_page_perms(self, group: Group, site: Site) -> None:
        filt = dict(
            content_type__app_label='wagtailcore',
            content_type__model='page',
        )
        root_page = site.root_page
        grp_perms = root_page.group_permissions.filter(group=group)  # pyright: ignore
        old_perms = set(grp_perms.values_list('permission', flat=True))
        new_perms = set(Permission.objects.filter(
            **filt,
            codename__in=self.page_perms,
        ))
        if old_perms != new_perms:
            logger.info('Setting new %s page permissions' % self.group_name)
            grp_perms.delete()
            objs = [GroupPagePermission(
                group=group,
                page=root_page,
                permission=perm,
            ) for perm in new_perms]
            GroupPagePermission.objects.bulk_create(objs)

    def create_or_update_instance_group(self, obj: M) -> Group:
        name = self.get_instance_group_name(obj)
        group = self.get_existing_instance_group(obj)
        if group is None:
            group = Group.objects.create(name=name)
            self.update_instance_group(obj, group)
        elif group.name != name:
            group.name = name
            group.save(update_fields=['name'])

        self._update_model_perms(group)
        if obj is not None:
            site = self.get_instance_site(obj)
            if site is not None:
                self._update_page_perms(group, site)

        return group


class AdminRole[M: Model](InstanceSpecificRole[M], abc.ABC):
    model_perms = [
        ('wagtailadmin', 'admin', ('access',)),
        ('wagtailcore', 'collection', ALL_MODEL_PERMS),
        ('wagtailimages', 'image', ALL_MODEL_PERMS),
    ]

    page_perms = set(PAGE_PERMISSION_CODENAMES)
