from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING, Any, ClassVar, Generic, cast
from typing_extensions import TypeVar

from django.contrib.auth.models import AnonymousUser
from django.db.models import Model, QuerySet
from django.forms import BaseModelForm
from wagtail.admin.forms.models import WagtailAdminModelForm
from wagtail.snippets.views.snippets import (
    CreateView,
    DeleteView,
    EditView,
    SnippetViewSet,
)

from kausal_common.admin_site.mixins import HideSnippetsFromBreadcrumbsMixin
from kausal_common.models.permission_policy import ModelPermissionPolicy, CreateContext
from kausal_common.models.permissions import PermissionedModel

from users.models import User

if TYPE_CHECKING:
    from django.http import HttpRequest
    from wagtail.permission_policies.base import BasePermissionPolicy

    from kausal_common.users import UserOrAnon

_ModelT = TypeVar('_ModelT', bound=Model, default=Model, covariant=True)  # noqa: PLC0105
_QS = TypeVar('_QS', bound=QuerySet[Any, Any], default=QuerySet[_ModelT, _ModelT])


class _ModelForm[M: Model](WagtailAdminModelForm[M, User]):
    pass

_FormT = TypeVar('_FormT', bound=BaseModelForm[Any], default=_ModelForm[_ModelT])


def user_has_permission(
    permission_policy: BasePermissionPolicy[Any, Any, Any],
    user: User | AnonymousUser,
    permission: str,
    obj: Model | None,
    context: HttpRequest | None = None,
) -> bool:
    assert isinstance(permission_policy, ModelPermissionPolicy)
    if isinstance(user, AnonymousUser):
        return False
    if permission == 'add':
        return permission_policy.user_can_create(user, context=context)
    assert obj is not None
    return permission_policy.user_has_permission_for_instance(
        user, permission, obj
    )


class PermissionedEditView(HideSnippetsFromBreadcrumbsMixin, EditView[_ModelT, _FormT]):
    def user_has_permission(self, permission):
        return user_has_permission(
            self.permission_policy,
            cast('UserOrAnon', self.request.user),
            permission,
            self.object
        )

    def get_editing_sessions(self):
        return None


class PermissionedDeleteView(DeleteView[_ModelT, _FormT]):
    def user_has_permission(self, permission):
        return user_has_permission(
            self.permission_policy,
            cast('UserOrAnon', self.request.user),
            permission,
            self.object
        )


class PermissionedCreateView(HideSnippetsFromBreadcrumbsMixin, CreateView[_ModelT, _FormT]):
    def user_has_permission(self, permission):
        return user_has_permission(
            self.permission_policy,
            cast('UserOrAnon', self.request.user),
            permission,
            None,
            context=self.get_create_context()
        )

    def get_create_context(self) -> CreateContext:
        return self.request


class PermissionedViewSet(Generic[_ModelT, _QS, _FormT], SnippetViewSet[_ModelT, _FormT]):
    add_view_class: ClassVar[type[PermissionedCreateView[_ModelT, _FormT]]]  # type: ignore[misc]
    edit_view_class: ClassVar[type[PermissionedEditView[_ModelT, _FormT]]]  # type: ignore[misc]
    # index_view_class: ClassVar = PathsIndexView[_ModelT, _QS]
    # delete_view_class: ClassVar = PathsDeleteView
    # usage_view_class: ClassVar = PathsUsageView

    add_to_admin_menu = True

    @cached_property
    def url_prefix(self) -> str:  # type: ignore[override]
        return f"{self.app_label}/{self.model_name}"

    @cached_property
    def url_namespace(self) -> str:  # type: ignore[override]
        return f"{self.app_label}_{self.model_name}"

    @property
    def permission_policy(self):
        if issubclass(self.model, PermissionedModel):
            return self.model.permission_policy()
        return super().permission_policy
