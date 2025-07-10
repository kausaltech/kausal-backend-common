from __future__ import annotations

from abc import abstractmethod
from enum import Enum
from typing import TYPE_CHECKING, Any, ClassVar, Self, cast
from typing_extensions import TypeVar

from django.db import models
from django.db.models import QuerySet
from graphql import GraphQLError
from modeltrans.manager import MultilingualManager
from modeltrans.translator import get_i18n_field
from pydantic import BaseModel, Field

from .types import ModelManager

if TYPE_CHECKING:
    from rich.repr import RichReprResult

    from kausal_common.graphene import GQLInfo
    from kausal_common.models.permission_policy import ModelPermissionPolicy
    from kausal_common.users import UserOrAnon

    from .permission_policy import ObjectSpecificAction


class PermissionedModel(models.Model):
    child_models: ClassVar[list[type[PermissionedModel]]] = []

    if TYPE_CHECKING:
        Meta: Any
    else:
        class Meta:
            abstract = True

    @abstractmethod
    def __str__(self) -> str: ...

    @abstractmethod
    def __rich_repr__(self) -> RichReprResult: ...

    @classmethod
    @abstractmethod
    def permission_policy(cls) -> ModelPermissionPolicy[Self, Any, Any]: ...

    def gql_action_allowed(self, info: GQLInfo, action: ObjectSpecificAction) -> bool:
        return self.permission_policy().gql_action_allowed(info, action, self)

    def ensure_gql_action_allowed(self, info: GQLInfo, action: ObjectSpecificAction) -> None:
        if not self.gql_action_allowed(info, action):
            raise GraphQLError("Permission denied for action '%s'" % action, nodes=info.field_nodes)


_Model = TypeVar('_Model', bound=PermissionedModel, covariant=True)  # noqa: PLC0105

class PermissionedQuerySet(QuerySet[_Model, _Model]):
    @property
    def _pp(self) -> ModelPermissionPolicy[_Model, Self, Any]:
        return self.model.permission_policy()

    def viewable_by(self, user: UserOrAnon) -> Self:
        return self._pp.filter_by_perm(self, user, 'view')
    def deletable_by(self, user: UserOrAnon) -> Self:
        return self._pp.filter_by_perm(self, user, 'delete')
    def modifiable_by(self, user: UserOrAnon) -> Self:
        return self._pp.filter_by_perm(self, user, 'change')


_PM = TypeVar("_PM", bound=PermissionedModel, covariant=True)  # noqa: PLC0105
_PQS = TypeVar(  # noqa: PLC0105
    "_PQS",
    bound=PermissionedQuerySet[PermissionedModel],
    default=PermissionedQuerySet[_PM], covariant=True
)

class PermissionedManager(MultilingualManager[_PM], ModelManager[_PM, _PQS]):
    """
    Manager for PermissionedModel instances.

    Will return instances of `PermissionedQuerySet`, unless overridden by a subclass.
    If the model has an i18n field, the queryset will also inherit from `MultilingualQuerySet`.
    """

    _queryset_class: type[QuerySet]

    def __init__(self) -> None:
        super().__init__()
        if self._queryset_class is QuerySet:
            self._queryset_class = PermissionedQuerySet

    if TYPE_CHECKING:
        def _patch_queryset[QS: QuerySet[Any]](self, qs: QS) -> QS: ...

    def get_queryset(self) -> _PQS:  # type: ignore[override]
        qs = super(ModelManager, self).get_queryset()
        if get_i18n_field(self.model):
            qs = self._patch_queryset(qs)
        return cast('_PQS', qs)


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
