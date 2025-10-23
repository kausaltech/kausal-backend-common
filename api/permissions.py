from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import TYPE_CHECKING

from django.db.models import ObjectDoesNotExist
from rest_framework import permissions
from rest_framework.exceptions import MethodNotAllowed, NotFound

from kausal_common.models.permissions import PermissionedModel
from kausal_common.users import user_or_none

if TYPE_CHECKING:
    from rest_framework.request import Request
    from rest_framework.views import APIView

    from kausal_common.models.permission_policy import BaseObjectAction, ModelPermissionPolicy


class _MetaClass(permissions.BasePermissionMetaclass, ABCMeta):  # type: ignore[misc]
    pass


class PermissionModelMeta[_M: PermissionedModel]:
    model: type[_M]
    allowed_actions: set[BaseObjectAction]


class PermissionPolicyDRFPermissionBase[_M: PermissionedModel, CreateContext](metaclass=_MetaClass):
    """
    A Django REST Framework Permission Class delegating to a Wagtail-style Permission Policy.

    Please subclass this and implement the get_create_context_from_api_view in order
    to be able to use this for a specific model. Also specify the main Model in
    Meta.model. The Django model permissions need to be properly set up for this
    class to work correctly.

    """

    Meta: PermissionModelMeta[_M]
    permission_policy: ModelPermissionPolicy[_M, CreateContext]
    allowed_actions: set[BaseObjectAction]

    HTTP_METHOD_TO_DJANGO_ACTION: dict[str, BaseObjectAction] = {
        'GET': 'view',
        'HEAD': 'view',
        'POST': 'add',
        'PUT': 'change',
        'OPTIONS': 'view',
        'PATCH': 'change',
        'DELETE': 'delete',
    }

    perms_map = {
        'GET': ['%(app_label)s.view_%(model_name)s'],
        'OPTIONS': [],
        'HEAD': ['%(app_label)s.view_%(model_name)s'],
        'POST': ['%(app_label)s.add_%(model_name)s'],
        'PUT': ['%(app_label)s.change_%(model_name)s'],
        'PATCH': ['%(app_label)s.change_%(model_name)s'],
        'DELETE': ['%(app_label)s.delete_%(model_name)s'],
    }

    def __init__(self):
        self.permission_policy = self.Meta.model.permission_policy()
        self.allowed_actions = getattr(self.Meta, 'allowed_actions', {'view', 'add', 'change', 'delete'})

    def http_method_to_django_action(self, method: str | None) -> BaseObjectAction:
        if method is None:
            raise ValueError('Invalid method')
        return self.HTTP_METHOD_TO_DJANGO_ACTION[method]

    def has_object_permission(self, request: Request, view, obj):
        if request.method is None:
            return False
        user = user_or_none(request.user)
        if user is None:
            return False
        model_action = self.HTTP_METHOD_TO_DJANGO_ACTION[request.method]
        assert model_action != 'add'
        if not self.permission_policy.user_has_perm(user, 'view', obj):
            # We want to report 404 so the existence of the resource
            # is not deducible from 404 vs 403
            self.code = 'not_found'
        return self.permission_policy.user_has_perm(user, model_action, obj)

    @abstractmethod
    def get_create_context_from_api_view(self, view: APIView) -> CreateContext: ...


class PermissionPolicyDRFPermission[_M: PermissionedModel, CreateContext](  # pyright: ignore[reportImplicitAbstractClass]
    PermissionPolicyDRFPermissionBase[_M, CreateContext], permissions.DjangoModelPermissions,
):
    def has_permission(self, request: Request, view: APIView):
        if request.method is None:
            return False

        user = user_or_none(request.user)
        if user is None:
            return False
        model_action = self.http_method_to_django_action(request.method)
        if model_action not in self.allowed_actions:
            raise MethodNotAllowed(request.method)
        if model_action == 'add':
            try:
                context = self.get_create_context_from_api_view(view)
            except ObjectDoesNotExist as e:
                raise NotFound() from e
            return self.permission_policy.user_can_create(user, context)
        # Delegates to basic Django model permissions, which need to be set up for the user's role.
        # After the model permissions return True, the has_object_permission method of this class
        # will be called to check out the object-level permissions.
        return super().has_permission(request, view)


class NestedPermissionModelMeta[M: PermissionedModel, NestedParent: PermissionedModel](PermissionModelMeta[M]):
    view_kwargs_parent_key: str
    nested_parent_key_field: str = 'uuid'
    nested_parent_model: type[NestedParent]


class NestedResourcePermissionPolicyDRFPermission[  # pyright: ignore[reportImplicitAbstractClass]
    M: PermissionedModel, CreateContext, NestedParent: PermissionedModel
](
    PermissionPolicyDRFPermissionBase[M, CreateContext], permissions.DjangoModelPermissions, metaclass=_MetaClass
):
    Meta: NestedPermissionModelMeta[M, NestedParent]

    perms_map = PermissionPolicyDRFPermissionBase.perms_map

    def get_nested_parent_from_api_view(self, view: APIView) -> NestedParent:
        lookup_value = view.kwargs[self.Meta.view_kwargs_parent_key]
        try:
            object = self.Meta.nested_parent_model._default_manager.get(**{self.Meta.nested_parent_key_field: lookup_value})
        except ObjectDoesNotExist as e:
            raise NotFound() from e
        return object

    def has_permission(self, request: Request, view: APIView):
        parent_obj = self.get_nested_parent_from_api_view(view)
        pp = parent_obj.permission_policy()
        user = user_or_none(request.user)
        if not user:
            return False
        if request.method is None:
            raise ValueError('No method supplied')
        action = self.http_method_to_django_action(request.method)
        if action not in self.allowed_actions:
            raise MethodNotAllowed(request.method)
        if not super().has_permission(request, view):
            return False
        if not pp.user_has_any_permission_for_instance(user, ['view'], parent_obj):
            raise NotFound()
        if action == 'add':
            try:
                context = self.get_create_context_from_api_view(view)
            except ObjectDoesNotExist as e:
                raise NotFound() from e
            return self.permission_policy.user_can_create(user, context)
        return True
