from typing import Any, override

from django.forms import Media
from django.http import HttpRequest
from django.utils.functional import cached_property
from django_stubs_ext import StrOrPromise
from wagtail.admin.ui.components import Component

"""Handles rendering of the list of actions in the footer of the page create/edit views."""
class ActionMenuItem(Component):
    """Defines an item in the actions drop-up on the page creation/edit view"""
    order: int | None = ...
    template_name: str = ...
    label: StrOrPromise = ...
    name: str = ...
    classname: str = ...
    icon_name: str = ...

    def __init__(self, order: int | None = None) -> None:
        ...

    def get_user_page_permissions_tester(self, context):
        ...

    def is_shown(self, context: dict[str, Any]) -> bool:
        """
        Whether this action should be shown on this request; permission checks etc should go here.
        By default, actions are shown for unlocked pages, hidden for locked pages

        context = dictionary containing at least:
            'request' = the current request object
            'view' = 'create', 'edit' or 'revisions_revert'
            'page' (if view = 'edit' or 'revisions_revert') = the page being edited
            'parent_page' (if view = 'create') = the parent page of the page being created
            'lock' = a Lock object if the page is locked, otherwise None
            'locked_for_user' = True if the lock prevents the current user from editing the page
            may also contain:
            'user_page_permissions_tester' = a PagePermissionTester for the current user and page
        """

    def get_context_data(self, parent_context: dict[str, Any]) -> dict[str, Any]:  # type: ignore[override]
        """Defines context for the template, overridable to use more data"""

    def get_url(self, parent_context: dict[str, Any]) -> str | None:
        ...



class PublishMenuItem(ActionMenuItem):
    def is_shown(self, context: dict[str, Any]) -> bool:
        ...

    def get_context_data(self, parent_context: dict[str, Any]) -> dict[str, Any]:
        ...



class SubmitForModerationMenuItem(ActionMenuItem):
    def is_shown(self, context: dict[str, Any]) -> bool:
        ...

    @override
    def get_context_data(self, parent_context: dict[str, Any]) -> dict[str, Any]:
        ...



class WorkflowMenuItem(ActionMenuItem):
    def __init__(self, name: str, label: StrOrPromise, launch_modal: bool, *args: Any, **kwargs: Any) -> None:
        ...

    def get_context_data(self, parent_context: dict[str, Any]) -> dict[str, Any]:
        ...

    def is_shown(self, context: dict[str, Any]) -> bool:
        ...



class RestartWorkflowMenuItem(ActionMenuItem):
    def is_shown(self, context: dict[str, Any]) -> bool:
        ...



class CancelWorkflowMenuItem(ActionMenuItem):
    def is_shown(self, context: dict[str, Any]) -> bool:
        ...



class UnpublishMenuItem(ActionMenuItem):
    def is_shown(self, context: dict[str, Any]) -> bool:
        ...

    def get_url(self, context: dict[str, Any]) -> str | None:
        ...



class SaveDraftMenuItem(ActionMenuItem):
    def get_context_data(self, parent_context: dict[str, Any]) -> dict[str, Any]:
        ...



class PageLockedMenuItem(ActionMenuItem):
    def is_shown(self, context: dict[str, Any]) -> bool: ...
    def get_context_data(self, parent_context: dict[str, Any]) -> dict[str, Any]: ...



BASE_PAGE_ACTION_MENU_ITEMS = ...
class PageActionMenu:
    def __init__(self, request: HttpRequest, **kwargs) -> None:
        ...

    def render_html(self):
        ...

    @cached_property
    def media(self) -> Media:
        ...
