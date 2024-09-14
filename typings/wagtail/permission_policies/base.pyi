from collections.abc import Sequence
from typing import Any, Generic, TypeAlias, TypeVar

from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import AnonymousUser
from django.db.models import Model, QuerySet
from django.utils.functional import cached_property

_Model = TypeVar('_Model', bound=Model, default=Model)
_UserT = TypeVar('_UserT', bound=AbstractBaseUser, default=AbstractBaseUser)
_PermT = TypeVar('_PermT', default=Any)
_AnyUser: TypeAlias = _UserT | AnonymousUser  # noqa: UP040

class BasePermissionPolicy(Generic[_Model, _UserT, _PermT]):
    """
    A 'permission policy' is an object that handles all decisions about the actions
    users are allowed to perform on a given model. The mechanism by which it does this
    is arbitrary, and may or may not involve the django.contrib.auth Permission model;
    it could be as simple as "allow all users to do everything".

    In this way, admin apps can change their permission-handling logic just by swapping
    to a different policy object, rather than having that logic spread across numerous
    view functions.

    BasePermissionPolicy is an abstract class that all permission policies inherit from.
    The only method that subclasses need to implement is users_with_any_permission;
    all other methods can be derived from that (but in practice, subclasses will probably
    want to override additional methods, either for efficiency or to implement more
    fine-grained permission logic).
    """
    permission_cache_name: str = ...

    def __init__(self, model: str | type[_Model]) -> None:
        ...

    @cached_property
    def model(self) -> type[_Model]: ...

    def check_model(self, model: str | type[_Model]) -> None: ...

    def get_all_permissions_for_user(self, user: AnonymousUser | _UserT) -> set[_PermT]:
        """
        Return a set of all permissions that the given user has on this model.

        They may be instances of django.contrib.auth.Permission, or custom
        permission objects defined by the policy, which are not necessarily
        model instances.
        """

    def get_cached_permissions_for_user(self, user: _AnyUser) -> set[_PermT]:
        """
        Return a list of all permissions that the given user has on this model,
        using the cache if available and populating the cache if not.

        This can be useful for the other methods to perform efficient queries
        against the set of permissions that the user has.
        """

    def user_has_permission(self, user: AnonymousUser | _UserT, action: str) -> bool:
        """
        Return whether the given user has permission to perform the given action
        on some or all instances of this model
        """

    def user_has_any_permission(self, user: AnonymousUser | _UserT, actions: Sequence[str]) -> bool:
        """
        Return whether the given user has permission to perform any of the given actions
        on some or all instances of this model
        """

    def users_with_any_permission(self, actions: Sequence[str]) -> QuerySet[_UserT, _UserT]:
        """
        Return a queryset of users who have permission to perform any of the given actions
        on some or all instances of this model
        """

    def users_with_permission(self, action: str) -> QuerySet[_UserT, _UserT]:
        """
        Return a queryset of users who have permission to perform the given action on
        some or all instances of this model
        """

    def user_has_permission_for_instance(self, user: _UserT, action: str, instance: _Model) -> bool:
        """
        Return whether the given user has permission to perform the given action on the
        given model instance
        """

    def user_has_any_permission_for_instance(self, user: _UserT, actions: Sequence[str], instance: _Model) -> bool:
        """
        Return whether the given user has permission to perform any of the given actions
        on the given model instance
        """

    def instances_user_has_any_permission_for(self, user: _UserT, actions: Sequence[str]) -> QuerySet[_Model, _Model]:
        """
        Return a queryset of all instances of this model for which the given user has
        permission to perform any of the given actions
        """

    def instances_user_has_permission_for(self, user: _UserT, action: str) -> QuerySet[_Model, _Model]:
        """
        Return a queryset of all instances of this model for which the given user has
        permission to perform the given action
        """

    def users_with_any_permission_for_instance(self, actions: Sequence[str], instance: _Model) -> QuerySet[_UserT, _UserT]:
        """
        Return a queryset of all users who have permission to perform any of the given
        actions on the given model instance
        """

    def users_with_permission_for_instance(self, action, instance: _Model) -> QuerySet[_UserT, _UserT]:
        ...



class BlanketPermissionPolicy(BasePermissionPolicy[_Model, _UserT, _PermT]):
    """
    A permission policy that gives everyone (including anonymous users)
    full permission over the given model
    """
    def user_has_permission(self, user: _AnyUser, action: str) -> bool: ...
    def user_has_any_permission(self, user: _AnyUser, actions: Sequence[str]) -> bool: ...

    #def users_with_any_permission(self, actions): # -> QuerySet[AbstractBaseUser, AbstractBaseUser]: ...

    #def users_with_permission(self, action): # -> QuerySet[AbstractBaseUser, AbstractBaseUser]: ...



class AuthenticationOnlyPermissionPolicy(BasePermissionPolicy):
    """
    A permission policy that gives all active authenticated users
    full permission over the given model
    """
    def user_has_permission(self, user, action):
        ...

    def user_has_any_permission(self, user, actions):
        ...

    def users_with_any_permission(self, actions): # -> QuerySet[AbstractBaseUser, AbstractBaseUser]:
        ...

    def users_with_permission(self, action): # -> QuerySet[AbstractBaseUser, AbstractBaseUser]:
        ...



class BaseDjangoAuthPermissionPolicy(BasePermissionPolicy[_Model, _UserT, _PermT]):
    """
    Extends BasePermissionPolicy with helper methods useful for policies that need to
    perform lookups against the django.contrib.auth permission model
    """
    def __init__(self, model: str | type[_Model], auth_model: str | type[_Model] | None = None) -> None: ...

    @cached_property
    def auth_model(self) -> type[_Model]: ...

    @cached_property
    def app_label(self) -> str: ...

    @cached_property
    def model_name(self) -> str: ...


class ModelPermissionPolicy(BaseDjangoAuthPermissionPolicy[_Model, _UserT, _PermT]):
    """
    A permission policy that enforces permissions at the model level, by consulting
    the standard django.contrib.auth permission model directly
    """
    def user_has_permission(self, user: AnonymousUser | _UserT, action: str) -> bool: ...

    def users_with_any_permission(self, actions: Sequence[str]) -> QuerySet[_UserT, _UserT]: ...


class OwnershipPermissionPolicy(BaseDjangoAuthPermissionPolicy[_Model, _UserT, _PermT]):
    """
    A permission policy for objects that support a concept of 'ownership', where
    the owner is typically the user who created the object.

    This policy piggybacks off 'add' and 'change' permissions defined through the
    django.contrib.auth Permission model, as follows:

    * any user with 'add' permission can create instances, and ALSO edit instances
    that they own
    * any user with 'change' permission can edit instances regardless of ownership
    * ability to edit also implies ability to delete

    Besides 'add', 'change' and 'delete', no other actions are recognised or permitted
    (unless the user is an active superuser, in which case they can do everything).
    """
    def __init__(self, model, auth_model=..., owner_field_name=...) -> None:
        ...

    def check_model(self, model): # -> None:
        ...

    def user_has_permission(self, user, action):
        ...

    def users_with_any_permission(self, actions): # -> QuerySet[AbstractBaseUser, AbstractBaseUser]:
        ...

    def user_has_permission_for_instance(self, user, action, instance): # -> bool:
        ...

    def user_has_any_permission_for_instance(self, user, actions, instance): # -> bool:
        ...

    def instances_user_has_any_permission_for(self, user, actions): # -> Any:
        ...

    def users_with_any_permission_for_instance(self, actions, instance): # -> QuerySet[AbstractBaseUser, AbstractBaseUser]:
        ...
