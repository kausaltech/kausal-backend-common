from __future__ import annotations

from abc import abstractmethod
from enum import Enum
from typing import TYPE_CHECKING, Any, ClassVar, Self, cast

from django.apps import apps
from django.core.checks import Error as CheckError, Warning as CheckWarning, register as register_check
from django.db.models import QuerySet
from modeltrans.manager import MultilingualManager
from modeltrans.translator import get_i18n_field
from pydantic import BaseModel, Field

from kausal_common.const import IS_WATCH
from kausal_common.strawberry.errors import PermissionDeniedError

from .types import AbstractModel, ModelManager

if TYPE_CHECKING:
    from collections.abc import Sequence

    from django.apps import AppConfig
    from django.core.checks import CheckMessage
    from django.db.models import Manager

    from rich.repr import RichReprResult

    from kausal_common.models.permission_policy import ModelPermissionPolicy
    from kausal_common.strawberry.helpers import InfoType
    from kausal_common.users import UserOrAnon

    from .permission_policy import ObjectSpecificAction


class PermissionedModel[CreateContext: Any = None](AbstractModel):  # pyright: ignore[reportImplicitAbstractClass]
    if TYPE_CHECKING:
        Meta: Any

        def __rich_repr__(self) -> RichReprResult: ...

    else:

        class Meta:
            abstract = True

    _registered_permissioned_child_models: ClassVar[list[type[PermissionedModel]]]

    @classmethod
    def __init_subclass__(cls, **kwargs) -> None:
        super().__init_subclass__(**kwargs)
        cls._registered_permissioned_child_models = []

    @abstractmethod
    def __str__(self) -> str: ...

    @classmethod
    def permissioned_child_models(cls) -> tuple[type[PermissionedModel], ...]:
        return tuple[type[PermissionedModel], ...](cls._registered_permissioned_child_models)

    @classmethod
    def register_permissioned_child_model(cls, child_model: type[PermissionedModel]) -> None:
        if child_model not in cls._registered_permissioned_child_models:
            cls._registered_permissioned_child_models.append(child_model)

    @classmethod
    @abstractmethod
    def permission_policy(cls) -> ModelPermissionPolicy[Any, Any, Any]: ...

    def gql_action_allowed(self, info: InfoType, action: ObjectSpecificAction, raise_on_denied: bool = True) -> bool:
        pp = self.permission_policy()
        is_allowed = pp.gql_action_allowed(info, action, self)
        if raise_on_denied and not is_allowed:
            block = pp.get_permission_block(action, obj=self)
            message = block.message if block is not None else "Permission denied for action '%s'" % action
            code = block.code if block is not None else None
            raise PermissionDeniedError(info, message, code=code)
        return is_allowed

    def ensure_gql_action_allowed(self, info: InfoType, action: ObjectSpecificAction) -> None:
        self.gql_action_allowed(info, action, raise_on_denied=True)

    @classmethod
    def gql_create_allowed(cls, info: InfoType, ctx: CreateContext, raise_on_denied: bool = True) -> bool:
        pp = cls.permission_policy()
        is_allowed = pp.gql_action_allowed(info, 'add', context=ctx)
        if raise_on_denied and not is_allowed:
            block = pp.get_permission_block('add', context=ctx)
            message = block.message if block is not None else 'Permission denied for create'
            code = block.code if block is not None else None
            raise PermissionDeniedError(info, message, code=code)
        return is_allowed


class PermissionedQuerySet[M: PermissionedModel[Any]](QuerySet[M, M]):
    if TYPE_CHECKING:

        @classmethod
        def as_manager(cls) -> Manager[M]: ...

    @property
    def _pp(self) -> ModelPermissionPolicy[M, Self, Any]:
        return self.model.permission_policy()

    def viewable_by(self, user: UserOrAnon) -> Self:
        return self._pp.filter_by_perm(self, user, 'view')

    def deletable_by(self, user: UserOrAnon) -> Self:
        return self._pp.filter_by_perm(self, user, 'delete')

    def modifiable_by(self, user: UserOrAnon) -> Self:
        return self._pp.filter_by_perm(self, user, 'change')

    def filter_by_perm(self, user: UserOrAnon, action: ObjectSpecificAction) -> Self:
        return self._pp.filter_by_perm(self, user, action)


class PermissionedManager[M: PermissionedModel, QS: PermissionedQuerySet[Any] = PermissionedQuerySet[M]](
    MultilingualManager[M], ModelManager[M, QS]
):
    """
    Manager for PermissionedModel instances.

    Will return instances of `PermissionedQuerySet`, unless overridden by a subclass.
    If the model has an i18n field, the queryset will also inherit from `MultilingualQuerySet`.
    """

    _queryset_class: type[QuerySet[Any]]

    def __init__(self) -> None:
        super().__init__()
        if self._queryset_class is QuerySet:
            self._queryset_class = PermissionedQuerySet

    if TYPE_CHECKING:

        def _patch_queryset[Q: QuerySet[Any]](self, _qs: Q) -> Q: ...

    def get_queryset(self) -> QS:
        qs = super(ModelManager, self).get_queryset()
        if get_i18n_field(self.model):
            qs = self._patch_queryset(qs)
        return cast('QS', qs)


class ModelAction(Enum):
    VIEW = 'view'
    CHANGE = 'change'
    ADD = 'add'
    DELETE = 'delete'


class UserPermissions(BaseModel):
    """Permissions for a user on a model instance."""

    view: bool
    change: bool
    delete: bool
    actions: list[ModelAction] = Field(default_factory=list)
    """List of actions the user is allowed to perform on the instance.

    These will correspond with `view`, `change`, `add`, and `delete` keys.
    """
    creatable_related_models: list[str] = Field(default_factory=list)
    other_permissions: list[str] = Field(default_factory=list)


def get_user_permissions_for_instance(user: UserOrAnon, obj: PermissionedModel) -> UserPermissions:
    from kausal_common.models.permission_policy import ALL_OBJECT_SPECIFIC_ACTIONS

    assert isinstance(obj, PermissionedModel)
    pp = obj.permission_policy()
    actions: list[ModelAction] = [
        ModelAction(action) for action in ALL_OBJECT_SPECIFIC_ACTIONS if pp.user_has_permission_for_instance(user, action, obj)
    ]
    obj_perms = UserPermissions(
        view=ModelAction.VIEW in actions,
        change=ModelAction.CHANGE in actions,
        delete=ModelAction.DELETE in actions,
        actions=actions,
        creatable_related_models=[model.__name__ for model in pp.creatable_child_models(user, obj)],
    )
    return obj_perms


@register_check
def check_permissioned_model(app_configs: Sequence[AppConfig] | None, **_kwargs) -> list[CheckMessage]:  # pyright: ignore[reportUnusedParameter]
    errors: list[CheckMessage] = []
    for model in apps.get_models():
        if not issubclass(model, PermissionedModel):
            continue
        if IS_WATCH:
            # FIXME: KW is lacking permission policies for these models.
            from kausal_common.datasets.models import DataPointComment, DatasetMetric, DatasetSourceReference

            if model in (DatasetMetric, DataPointComment, DatasetSourceReference):
                continue
        try:
            pp = model.permission_policy()
            if pp is None:  # pyright: ignore[reportUnnecessaryComparison]
                qs = model._default_manager.get_queryset()
                if qs.query.order_by:
                    # Default manager has an order_by, so we can skip this model.
                    continue
                errors.append(CheckWarning('Permissioned model has no permission policy', id='kausal_common.P001', obj=model))
                continue
            if pp.model != model:
                errors.append(
                    CheckError('Permissioned model has permission policy for wrong model', id='kausal_common.P002', obj=model)
                )
                continue
        except AttributeError:
            errors.append(CheckWarning('Permissioned model has no permission policy', id='kausal_common.P001', obj=model))
    return errors
