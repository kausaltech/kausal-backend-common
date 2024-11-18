from __future__ import annotations

from abc import abstractmethod
from enum import Enum
from typing import TYPE_CHECKING, Any, ClassVar, Self
from typing_extensions import TypeVar

from django.db import models
from django.db.models import QuerySet
from graphql import GraphQLError
from pydantic import BaseModel, Field

from kausal_common.models.permission_policy import ALL_OBJECT_SPECIFIC_ACTIONS

if TYPE_CHECKING:
    from kausal_common.graphene import GQLInfo
    from kausal_common.models.permission_policy import ModelPermissionPolicy
    from kausal_common.users import UserOrAnon

    from .permission_policy import ObjectSpecificAction


class PermissionedModel(models.Model):  # noqa: DJ008
    child_models: ClassVar[list[type[PermissionedModel]]] = []

    if TYPE_CHECKING:
        Meta: Any
    else:
        class Meta:
            abstract = True

    @classmethod
    @abstractmethod
    def permission_policy(cls) -> ModelPermissionPolicy[Self, Any]: ...

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
