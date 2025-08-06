from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Generic, Literal, TypeGuard, cast, overload
from typing_extensions import TypeVar

from django.contrib.auth.models import AnonymousUser
from django.db.models import Q
from django.db.models.query import QuerySet
from wagtail.permission_policies.base import ModelPermissionPolicy as WagtailModelPermissionPolicy

from loguru import logger

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from kausal_common.graphene import GQLInfo
    from kausal_common.models.types import QS
    from kausal_common.users import UserOrAnon

    from users.models import User

    from .permissions import PermissionedModel


_M = TypeVar('_M', bound='PermissionedModel')
_QS = TypeVar('_QS', bound=QuerySet, default=QuerySet[_M])
CreateContext = TypeVar('CreateContext', default=Any)

type BaseObjectAction = Literal['view', 'add', 'change', 'delete']
type ObjectSpecificAction = Literal['view', 'change', 'delete']

ALL_OBJECT_SPECIFIC_ACTIONS: tuple[ObjectSpecificAction, ...] = ('view', 'change', 'delete')


def is_base_action(action: str) -> TypeGuard[ObjectSpecificAction]:
    return action in ('view', 'change', 'delete')


class ModelPermissionPolicy(Generic[_M, CreateContext, _QS], ABC, WagtailModelPermissionPolicy[_M, 'User', Any]):
    public_fields: list[str]
    """List of fields that are public."""

    def __init__(self, model: type[_M]):
        super().__init__(model)
        pf = getattr(model, 'public_fields', None)
        self_pf = getattr(self, 'public_fields', None)
        if self_pf is None:
            if pf is not None:
                self_pf = list(pf)
            else:
                self_pf = []
        self.public_fields = self_pf

    def is_create_context_valid(self, context: Any) -> TypeGuard[CreateContext]:
        return False

    @staticmethod
    def user_is_authenticated(user: UserOrAnon | None) -> TypeGuard[User]:
        if user is None or isinstance(user, AnonymousUser):
            return False
        return user.is_authenticated and user.is_active

    @abstractmethod
    def construct_perm_q(self, user: User, action: ObjectSpecificAction) -> Q | None:
        """
        Construct a Q object for determining the permissions for the action for a user.

        Returns None if no objects are allowed, and Q otherwise.
        """

    @abstractmethod
    def construct_perm_q_anon(self, action: ObjectSpecificAction) -> Q | None:
        """
        Construct a Q object for determining the permissions for the action for anonymous users.

        Returns None no objects are allowed, and Q otherwise.
        """

    @abstractmethod
    def user_has_perm(self, user: User, action: ObjectSpecificAction, obj: _M) -> bool:
        """Check if user has permission to perform an action on an instance."""

    @abstractmethod
    def anon_has_perm(self, action: ObjectSpecificAction, obj: _M) -> bool:
        """Check if an unauthenticated user has permission to perform an action on an instance."""

    @abstractmethod
    def user_can_create(self, user: User, context: CreateContext) -> bool:
        """Check if user can create a new object."""

    def creatable_child_models(self, user: UserOrAnon, obj: _M) -> Sequence[type[PermissionedModel]]:
        """
        Return a list of related models that the user can create.

        The child models are typically associated with the current model via a ForeignKey or OneToOneField.
        """
        creatable_child_models: list[type[PermissionedModel]] = []
        for child_model in self.model.child_models:
            pp = child_model.permission_policy()
            if isinstance(pp, ParentInheritedPolicy):
                if self.user_is_authenticated(user):
                    if pp.user_can_create(user, obj):
                        creatable_child_models.append(child_model)
                elif pp.anon_can_create(obj):
                    creatable_child_models.append(child_model)
        return creatable_child_models

    def anon_can_create(self, context: CreateContext) -> bool:
        """Check if an unauthenticated user can create a new object."""
        return False

    def get_queryset(self) -> _QS:
        mgr = getattr(self.model, 'objects', self.model._default_manager)
        return cast('_QS', mgr.get_queryset())

    @overload
    def gql_action_allowed(
        self, info: GQLInfo, action: Literal['add'], obj: None = ..., context: CreateContext = ...,
    ) -> bool: ...

    @overload
    def gql_action_allowed(
        self, info: GQLInfo, action: ObjectSpecificAction, obj: _M = ..., context: None = ...,
    ) -> bool: ...

    def gql_action_allowed(
        self, info: GQLInfo, action: BaseObjectAction, obj: _M | None = None, context: CreateContext | None = None,
    ) -> bool:
        user = info.context.user
        if action == 'add':
            if not self.is_create_context_valid(context):
                raise TypeError("Invalid create context type for %s: %s" % (
                    type(self), context,
                ))
            if not self.user_is_authenticated(user):
                return self.anon_can_create(context)
            return self.user_can_create(user, context)

        if obj is None:
            return False
        if not self.user_is_authenticated(user):
            return self.anon_has_perm(action, obj)
        return self.user_has_perm(user, action, obj)

    def user_has_permission(self, user: UserOrAnon, action: str) -> bool:
        return super().user_has_permission(user, action)

    def user_has_any_permission(self, user: UserOrAnon, actions: Sequence[str]) -> bool:
        return any(self.user_has_permission(user, action) for action in actions)

    def _construct_q(self, user: UserOrAnon, action: ObjectSpecificAction) -> Q | None:
        if not self.user_is_authenticated(user):
            return self.construct_perm_q_anon(action)
        if user.is_superuser:
            return Q()
        return self.construct_perm_q(user, action)

    def filter_by_perm(self, qs: _QS, user: UserOrAnon, action: ObjectSpecificAction) -> _QS:
        q = self._construct_q(user, action)
        if q is None:
            return qs.none()
        return qs.filter(q).distinct()

    def instances_user_has_permission_for(self, user: UserOrAnon, action: str) -> _QS:
        return self.instances_user_has_any_permission_for(user, [action])

    def instances_user_has_any_permission_for(self, user: UserOrAnon, actions: Sequence[str]) -> _QS:
        qs = self.get_queryset()
        if self.user_is_authenticated(user) and user.is_superuser:
            return qs
        filters = None
        for action in actions:
            if not is_base_action(action):
                logger.error("Unknown action: %s" % action)
                return qs.none()
            q = self._construct_q(user, action)
            if q is None:
                continue
            if filters is None:
                filters = q
            else:
                filters |= q
        if filters is None:
            return qs.none()
        return qs.filter(filters).distinct()

    def user_has_permission_for_instance(self, user: UserOrAnon, action: str, instance: _M) -> bool:
        if not is_base_action(action):
            logger.error("Unknown action: %s" % action)
            return False
        if not self.user_is_authenticated(user):
            return self.anon_has_perm(action, instance)
        if user.is_superuser:
            return True
        return self.user_has_perm(user, action, instance)

    def is_field_visible(self, instance: _M, field_name: str, user: UserOrAnon | None) -> bool:
        if field_name in self.public_fields:
            return True
        if not self.user_is_authenticated(user):
            return False
        return self.user_has_any_permission_for_instance(user, ['change', 'add', 'delete'], instance)


class ModelReadOnlyPolicy(ModelPermissionPolicy[_M, CreateContext, _QS]):
    def construct_perm_q(self, user: User, action: BaseObjectAction) -> Q | None:
        if user.is_superuser or action == 'view':
            return Q()
        return None

    def construct_perm_q_anon(self, action: BaseObjectAction) -> Q | None:
        if action == 'view':
            return Q()
        return None

    def user_has_perm(self, user: User, action: ObjectSpecificAction, obj: _M) -> bool:
        return user.is_superuser or action == 'view'

    def anon_has_perm(self, action: ObjectSpecificAction, obj: _M) -> bool:
        return action == 'view'

    def user_can_create(self, user: User, context: CreateContext) -> bool:
        if user.is_superuser:
            return True
        return False

    def user_has_permission(self, user: UserOrAnon, action: str) -> bool:
        if user.is_superuser:
            return True
        return action == 'view'


_ParentM = TypeVar('_ParentM', bound='PermissionedModel')


class ParentInheritedPolicy(Generic[_M, _ParentM, _QS], ModelPermissionPolicy[_M, _ParentM, _QS]):
    parent_model: type[_ParentM]
    parent_policy: ModelPermissionPolicy[_ParentM, Any, QS[_ParentM]]
    disallowed_actions: set[BaseObjectAction]

    def __init__(
        self,
        model: type[_M],
        parent_model: type[_ParentM],
        parent_field: str,
        disallowed_actions: Iterable[BaseObjectAction] = (),
    ):
        super().__init__(model)
        self.parent_model = parent_model
        self.parent_policy = parent_model.permission_policy()
        self.parent_field = parent_field
        if model not in self.parent_model.child_models:
            self.parent_model.child_models.append(model)
        self.disallowed_actions = set(disallowed_actions)

    def parent_in_q(self, val: QuerySet) -> Q:
        key = '%s__in' % self.parent_field
        return Q(**{key: val})

    def get_parent_qs(self, user: UserOrAnon, action: BaseObjectAction) -> QS[_ParentM]:
        return self.parent_policy.instances_user_has_permission_for(user, action)

    def get_parent_obj(self, obj: _M) -> _ParentM:
        return getattr(obj, self.parent_field)

    def construct_perm_q(self, user: User, action: BaseObjectAction) -> Q | None:
        if action in self.disallowed_actions:
            return None
        return self.parent_in_q(self.get_parent_qs(user, action))

    def construct_perm_q_anon(self, action: BaseObjectAction) -> Q | None:
        if action in self.disallowed_actions:
            return None
        return self.parent_in_q(self.get_parent_qs(AnonymousUser(), action))

    def user_has_perm(self, user: User, action: ObjectSpecificAction, obj: _M) -> bool:
        if action in self.disallowed_actions:
            return False
        return self.parent_policy.user_has_perm(user, action, getattr(obj, self.parent_field))

    def anon_has_perm(self, action: ObjectSpecificAction, obj: _M) -> bool:
        if action in self.disallowed_actions:
            return False
        return self.parent_policy.anon_has_perm(action, self.get_parent_obj(obj))

    def user_can_create(self, user: User, context: _ParentM) -> bool:
        if 'add' in self.disallowed_actions:
            return False
        # Default to the permission to edit the parent object
        return self.parent_policy.user_has_perm(user, 'change', context)

    def user_has_any_permission(self, user: User | AnonymousUser, actions: Sequence[str]) -> bool:
        return self.parent_policy.user_has_any_permission(user, actions)
