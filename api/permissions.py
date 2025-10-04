from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import TYPE_CHECKING

from rest_framework import permissions

from kausal_common.models.permissions import PermissionedModel
from kausal_common.users import user_or_none

if TYPE_CHECKING:
    from rest_framework.request import Request
    from rest_framework.views import APIView

    from kausal_common.models.permission_policy import BaseObjectAction, ModelPermissionPolicy

    from users.models import User


class _MetaClass(permissions.BasePermissionMetaclass, ABCMeta):
    pass


class PermissionModelMeta[_M: PermissionedModel]:
    model: type[_M]


class PermissionPolicyDRFPermission[_M: PermissionedModel, CreateContext](  # pyright: ignore[reportImplicitAbstractClass]
    permissions.DjangoModelPermissions,
    metaclass=_MetaClass
):
    """
    A Django REST Framework Permission Class delegating to a Wagtail-style Permission Policy.

    Please subclass this and implement the get_create_context_from_api_view in order
    to be able to use this for a specific model. Also specify the main Model in
    Meta.model. The Django model permissions need to be properly set up for this
    class to work correctly.

    """

    Meta: PermissionModelMeta[_M]
    permission_policy: ModelPermissionPolicy[_M, CreateContext]

    HTTP_METHOD_TO_DJANGO_ACTION: dict[str, BaseObjectAction] = {
        'GET': 'view',
        'POST': 'add',
        'PUT': 'change',
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

    def has_permission(self, request: Request, view: APIView):
        if request.method is None:
            return False
        user = user_or_none(request.user)
        if user is None:
            return False
        model_action = self.HTTP_METHOD_TO_DJANGO_ACTION[request.method]
        if model_action == 'add':
            context = self.get_create_context_from_api_view(view)
            return self.permission_policy.user_can_create(user, context)
        # Delegates to basic Django model permissions, which need to be set up for the user's role.
        # After the model permissions return True, the has_object_permission method of this class
        # will be called to check out the object-level permissions.
        return super().has_permission(request, view)

    def has_object_permission(self, request: Request, view, obj):
        if request.method is None:
            return False
        user = user_or_none(request.user)
        if user is None:
            return False
        model_action = self.HTTP_METHOD_TO_DJANGO_ACTION[request.method]
        assert model_action != 'add'
        return self.permission_policy.user_has_perm(user, model_action, obj)

    @abstractmethod
    def get_create_context_from_api_view(self, view: APIView) -> CreateContext: ...
