from __future__ import annotations

import abc
from dataclasses import dataclass, field
from functools import cache, cached_property
from typing import TYPE_CHECKING, Any, ClassVar, Generic, Literal, Protocol, cast, overload
from typing_extensions import TypeVar

from django.contrib.auth import get_permission_codename
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.checks import CheckMessage, Error
from django.core.exceptions import FieldDoesNotExist
from django.db.models import Model, Q, QuerySet
from django.db.models.fields.related import ForeignKey
from wagtail.models import PAGE_PERMISSION_CODENAMES

from loguru import logger

if TYPE_CHECKING:
    from collections.abc import Generator, Sequence

    from django_stubs_ext import StrPromise
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

    def __str__(self) -> str:
        return 'Role %s (%s)' % (self.id, str(self.name))

    def check(self) -> list[CheckMessage]:
        from django.apps import apps

        allow_list = {'wagtailadmin.access_admin'}

        errors: list[CheckMessage] = []
        for app_label, app_perms in self._app_model_perms.items():
            app = apps.app_configs.get(app_label)
            if app is None:
                error = Error(
                    f'Role {self.id} has permissions for non-existing app {app_label}', id='kausal_common.R001', obj=self
                )
                errors.append(error)
                continue
            model_perms = set()
            for model in app.get_models():
                meta = model._meta
                for action in meta.default_permissions:
                    model_perms.add(get_permission_codename(action, meta))
                for codename in meta.permissions:
                    model_perms.add(codename)
            for perm_str in app_perms:
                if perm_str in model_perms:
                    continue
                if f'{app_label}.{perm_str}' in allow_list:
                    continue
                error = Error(
                    f'Role has invalid permission {perm_str} for app {app_label}',
                    id='kausal_common.R002',
                    obj=self,
                )
                errors.append(error)

        return errors

    @cached_property
    def perms_by_app(self):
        perms = Permission.objects.filter(content_type__app_label__in=self._app_model_perms.keys()).select_related('content_type')
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
            logger.info('Permission changes detected in group %s, setting new permissions' % str(group))
            group.permissions.set(new_perms)

    def get_actions_for_model(self, model: type[Model]) -> set[str]:
        return self._get_actions_for_model(model._meta.app_label, model._meta.model_name)

    def refresh(self):
        group, _ = Group.objects.get_or_create(name=str(self.name))
        self._update_model_perms(group)

    def __rich_repr__(self) -> Generator[tuple[str, Any], Any]:
        yield 'id', self.id
        yield 'name', self.name


class InstanceSpecificRole[M: Model](Role, abc.ABC):
    model: type[M]

    def __init__(self, model: type[M]):
        self.model = model
        super().__init__()

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
        from wagtail.models import GroupPagePermission

        filt = dict(
            content_type__app_label='wagtailcore',
            content_type__model='page',
        )
        root_page = site.root_page
        grp_perms = GroupPagePermission.objects.filter(page=root_page, group=group)
        old_perms: set[Permission] = set(Permission.objects.filter(grouppagepermission__in=grp_perms).distinct())
        new_perms = set(
            Permission.objects.filter(
                **filt,
                codename__in=self.page_perms,
            )
        )
        if old_perms != new_perms:
            logger.info('Setting new %s page permissions' % str(group))
            grp_perms.delete()
            objs = [
                GroupPagePermission(
                    group=group,
                    page=root_page,
                    permission=perm,
                )
                for perm in new_perms
            ]
            GroupPagePermission.objects.bulk_create(objs)

    def _update_permissions(self, obj: M, group: Group) -> None:
        self._update_model_perms(group)
        if obj is not None:
            site = self.get_instance_site(obj)
            if site is not None:
                self._update_page_perms(group, site)

    def create_or_update_instance_group(self, obj: M) -> Group:
        name = self.get_instance_group_name(obj)
        group = self.get_existing_instance_group(obj)
        if group is None:
            group = Group.objects.create(name=name)
            self.update_instance_group(obj, group)
        elif group.name != name:
            group.name = name
            group.save(update_fields=['name'])

        self._update_permissions(obj, group)

        return group

    def assign_user(self, obj: M, user: User) -> bool:
        obj_group = self.get_existing_instance_group(obj)
        if obj_group is None:
            obj_group = self.create_or_update_instance_group(obj)
        if obj_group in user.groups.all():
            return False
        user.groups.add(obj_group)
        logger.info('Assign role %s for user %s' % (str(self.get_instance_group_name(obj)), user))
        return True

    def unassign_user(self, obj: M, user: User) -> bool:
        obj_group = self.get_existing_instance_group(obj)
        if obj_group is None:
            return False
        if obj_group not in user.groups.all():
            return False
        user.groups.remove(obj_group)
        logger.info('Unassign role %s for user %s' % (str(self.get_instance_group_name(obj)), user))
        return True

    def __rich_repr__(self):
        yield from super().__rich_repr__()
        yield 'model', self.model


_ModelT = TypeVar('_ModelT', bound=Model)
_QS = TypeVar('_QS', bound=QuerySet[Any, Any], default=QuerySet[_ModelT, _ModelT], covariant=True)  # noqa: PLC0105


class InstanceFieldGroupRole(Generic[_ModelT, _QS], InstanceSpecificRole[_ModelT], abc.ABC):
    instance_group_field_name: ClassVar[str]

    def check(self) -> list[CheckMessage]:
        errors = super().check()

        field_name = getattr(self, 'instance_group_field_name', None)
        if field_name is None:
            errors.append(
                Error(
                    'Role has no instance_group_field_name',
                    id='kausal_common.R003',
                    obj=self,
                )
            )
            return errors

        meta = self.model._meta
        try:
            field = meta.get_field(field_name)
        except FieldDoesNotExist:
            errors.append(
                Error(
                    'Role has invalid instance_group_field_name %s' % field_name,
                    id='kausal_common.R004',
                    obj=self,
                )
            )
            return errors

        if not isinstance(field, ForeignKey) or field.related_model != Group:
            errors.append(
                Error(
                    '%s.%s does not point to a Group' % (self.model._meta.model, field_name),
                    id='kausal_common.R005',
                    obj=self,
                )
            )
        return errors

    def delete_instance_group(self, obj: _ModelT):
        grp: Group | None = getattr(obj, self.instance_group_field_name)
        if grp is None:
            return
        mgr = self.model._default_manager
        g_id: int = getattr(self, '%s_id' % self.instance_group_field_name)
        filters = {
            self.instance_group_field_name: g_id,
        }
        has_others = mgr.filter(**filters).exclude(pk=obj.pk).exists()
        if has_others:
            return
        setattr(obj, self.instance_group_field_name, None)
        update = {
            self.instance_group_field_name: None,
        }
        mgr.filter(id=obj.pk).update(**update)
        Group.objects.get(id=g_id).delete()

    def get_instances_for_user(self, user: User) -> _QS:
        return cast('_QS', self.model._default_manager.filter(self.role_q(user)).distinct())

    def role_q(self, user: User, prefix: str | None = None) -> Q:
        q_str = f'{self.instance_group_field_name}__in'
        if prefix is not None:
            q_str = f'{prefix}__{q_str}'
        return Q(**{q_str: user.cgroups})


class AdminRole[M: Model](InstanceSpecificRole[M], abc.ABC):
    model_perms = [
        ('wagtailadmin', 'admin', ('access',)),
        ('wagtailcore', 'collection', ALL_MODEL_PERMS),
        ('wagtailimages', 'image', ALL_MODEL_PERMS),
    ]

    page_perms = set(PAGE_PERMISSION_CODENAMES)


class RoleRegistry:
    def __init__(self):
        self.roles: dict[str, InstanceSpecificRole[Any]] = {}
        super().__init__()

    def register(self, role: InstanceSpecificRole[Any]):
        """Register a role in the role registry."""
        from .roles import InstanceSpecificRole

        if not isinstance(role, InstanceSpecificRole):  # pyright: ignore[reportUnnecessaryIsInstance]
            msg = f'Only InstanceSpecificRole instances can be registered. Got {role}'
            raise TypeError(msg)

        if role.id in self.roles:
            msg = f"Role with id '{role.id}' is already registered"
            raise ValueError(msg)

        self.roles[role.id] = role

    def get_role(self, role_id: str) -> InstanceSpecificRole[Any]:
        """Get a role by its ID."""
        if role_id not in self.roles:
            msg = f"No role registered with id '{role_id}'"
            raise KeyError(msg)
        return self.roles[role_id]

    def get_all_roles(self) -> list[InstanceSpecificRole[Any]]:
        """Get all registered roles."""
        return list(self.roles.values())


role_registry = RoleRegistry()


def register_role(role: InstanceSpecificRole[Any]):
    return role_registry.register(role)


@dataclass
class UserPermissionCache:
    user: User
    instance_roles: dict[str, set[int]] = field(default_factory=dict)

    @overload
    def has_instance_role[M: Model](self, role: InstanceSpecificRole[M], obj: M) -> bool: ...

    @overload
    def has_instance_role(self, role: str, obj: Model) -> bool: ...

    def has_instance_role(self, role: str | InstanceSpecificRole[Any], obj: Model) -> bool:
        if isinstance(role, str):
            role = role_registry.get_role(role)
        if not isinstance(obj, role.model):
            raise TypeError('%s is not an instance of %s' % (obj, role.model))
        role_objs = self.instance_roles.get(role.id)
        if role_objs is None:
            role_objs = set(obj.pk for obj in role.get_instances_for_user(self.user))
            self.instance_roles[role.id] = role_objs
        return obj.pk in role_objs

    def get_roles_for_instance(self, obj: Model) -> list[InstanceSpecificRole[Any]] | None:
        """
        Return the roles the user has for a given model instance.

        If no roles are configured for the model, will return None.
        """
        roles: list[InstanceSpecificRole[Any]] = []
        model_has_roles = False

        for role in role_registry.get_all_roles():
            if role.model is not type(obj):
                continue
            model_has_roles = True
            if self.has_instance_role(role, obj):
                roles.append(role)
        if not model_has_roles:
            return None
        return roles

    def refresh_role_permissions(self):
        """Ensure the groups associated with the roles have up-to-date permissions."""
        for role in role_registry.get_all_roles():
            objs = role.get_instances_for_user(self.user)
            for obj in objs:
                role.create_or_update_instance_group(obj)
