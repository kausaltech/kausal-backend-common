from functools import cache
from typing import Any

from django.forms.widgets import Media
from django.utils.functional import cached_property
from django_stubs_ext import StrOrPromise
from wagtail.admin.ui.components import Component

"""Handles rendering of the list of actions in the footer of the snippet create/edit views."""
class ActionMenuItem(Component):
    """Defines an item in the actions drop-up on the snippet creation/edit view"""
    order: int = ...
    template_name: str = ...
    label: StrOrPromise = ...
    name: str = ...
    classname: str = ...
    icon_name: str = ...
    def __init__(self, order: int =...) -> None:
        ...

    def is_shown(self, context: dict[str, Any]) -> bool:
        """
        Whether this action should be shown on this request; permission checks etc should go here.

        request = the current request object

        context = dictionary containing at least:
            'view' = 'create' or 'edit'
            'model' = the model of the snippet being created/edited
            'instance' (if view = 'edit') = the snippet being edited
        """

    def get_context_data(self, parent_context: dict[str, Any]) -> dict[str, Any]:  # type: ignore[override]
        """Defines context for the template, overridable to use more data"""

    def get_url(self, parent_context: dict[str, Any]) -> str | None:
        ...



class PublishMenuItem(ActionMenuItem): ...

class SubmitForModerationMenuItem(ActionMenuItem): ...
class RestartWorkflowMenuItem(ActionMenuItem): ...
class CancelWorkflowMenuItem(ActionMenuItem): ...


class UnpublishMenuItem(ActionMenuItem): ...

class SaveMenuItem(ActionMenuItem): ...

class LockedMenuItem(ActionMenuItem): ...


@cache
def get_base_snippet_action_menu_items(
    model,
) -> list[ActionMenuItem]:
    """
    Retrieve the global list of menu items for the snippet action menu,
    which may then be customised on a per-request basis
    """

class SnippetActionMenu:
    template = ...
    def __init__(self, request, **kwargs) -> None:
        ...

    def render_html(self) -> str:
        ...

    @cached_property
    def media(self) -> Media:
        ...
