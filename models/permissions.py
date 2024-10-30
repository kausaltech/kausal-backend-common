from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, Any, Self
from typing_extensions import TypeVar

from django.db import models
from django.db.models import QuerySet
from graphql import GraphQLError

if TYPE_CHECKING:
    from kausal_common.graphene import GQLInfo
    from kausal_common.models.permission_policy import ModelPermissionPolicy
    from kausal_common.users import UserOrAnon

    from .permission_policy import ObjectSpecificAction


class PermissionedModel(models.Model):  # noqa: DJ008
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
