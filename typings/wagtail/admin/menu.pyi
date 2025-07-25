from collections.abc import Sequence
from typing import Any, ClassVar, TypedDict, Unpack

from django.forms.widgets import Media, MediaDefiningClass
from django.http.request import HttpRequest
from django.utils.functional import StrOrPromise, cached_property as cached_property
from wagtail import hooks as hooks
from wagtail.admin.ui.sidebar import MenuItem as SidebarMenuItem
from wagtail.coreutils import cautious_slugify as cautious_slugify
from wagtail.utils.deprecation import RemovedInWagtail70Warning as RemovedInWagtail70Warning

class MenuItemInit(TypedDict, total=False):
    classname: str
    icon_name: str
    name: str
    attrs: dict[str, Any]
    order: int


class MenuItem(metaclass=MediaDefiningClass):
    label: StrOrPromise
    url: str
    classname: str
    icon_name: str
    name: str
    attrs: dict[str, str]
    order: int
    def __init__(
        self,
        label: StrOrPromise,
        url: str,
        **kwargs: Unpack[MenuItemInit]
    ) -> None: ...
    def is_shown(self, request: HttpRequest) -> bool:
        """
        Whether this menu item should be shown for the given request; permission
        checks etc should go here. By default, menu items are shown all the time
        """
    def is_active(self, request: HttpRequest) -> bool: ...
    def render_component(self, request: HttpRequest) -> SidebarMenuItem: ...

class DismissibleMenuItemMixin:
    def __init__(self, *args, **kwargs) -> None: ...
    def render_component(self, request: HttpRequest): ...

class DismissibleMenuItem(DismissibleMenuItemMixin, MenuItem): ...

class Menu:
    register_hook_name: str | None
    construct_hook_name: str | None
    initial_menu_items: Sequence[MenuItem] | None
    def __init__(
        self,
        register_hook_name: str | None = None,
        construct_hook_name: str | None = None,
        items: Sequence[MenuItem] | None = None,
    ) -> None: ...
    @cached_property
    def registered_menu_items(self) -> Sequence[MenuItem]: ...
    def menu_items_for_request(self, request: HttpRequest) -> Sequence[MenuItem]: ...
    @property
    def media(self) -> Media: ...
    def render_component(self, request: HttpRequest) -> SidebarMenuItem: ...

class SubmenuMenuItem(MenuItem):
    """A MenuItem which wraps an inner Menu object"""

    menu: Menu
    def __init__(self, label: StrOrPromise, menu: Menu, **kwargs: Any) -> None: ...
    def is_shown(self, request: HttpRequest) -> bool: ...
    def render_component(self, request: HttpRequest) -> SidebarMenuItem: ...

class DismissibleSubmenuMenuItem(DismissibleMenuItemMixin, SubmenuMenuItem): ...

class AdminOnlyMenuItem(MenuItem):
    """A MenuItem which is only shown to superusers"""
    def is_shown(self, request: HttpRequest) -> bool: ...

class WagtailMenuRegisterable:
    menu_icon: str
    menu_label: StrOrPromise
    menu_name: str
    menu_order: int
    menu_url: str | None
    add_to_admin_menu: bool = False
    add_to_settings_menu: bool = False

    menu_item_class: ClassVar[type[MenuItem]]
    """A ``wagtail.admin.menu.MenuItem`` subclass to be registered with a menu hook."""

    def get_menu_item(self, order: int | None = None) -> MenuItem:
        """
        Returns a ``wagtail.admin.menu.MenuItem`` instance to be registered
        with the Wagtail admin.

        The ``order`` parameter allows the method to be called from the outside
        (e.g. a ``ViewSetGroup``) to create a sub menu item with
        the correct order.
        """

    @cached_property
    def menu_hook(self) -> str:
        """
        The name of the hook to register the menu item within.

        This takes precedence over ``add_to_admin_menu`` and ``add_to_settings_menu``.
        """

    def register_menu_item(self) -> None:
        """Registers the menu item with the Wagtail admin."""


class WagtailMenuRegisterableGroup(WagtailMenuRegisterable):
    """
    A container for grouping together multiple WagtailMenuRegisterable instances.
    Creates a menu item with a submenu for accessing the main URL for each instances.
    """

    items: Sequence[WagtailMenuRegisterable]
    menu_icon: str
    add_to_admin_menu: bool
    registerables: Sequence[WagtailMenuRegisterable]

    def __init__(self) -> None:
        """
        When initialising, instantiate the classes (or use the instances)
        within 'items', and assign the list to a ``registerables`` attribute.
        """
    def get_submenu_items(self) -> Sequence[MenuItem]: ...
    def get_menu_item(self, order: int | None = None) -> MenuItem: ...

admin_menu: Menu
settings_menu: Menu
reports_menu: Menu
help_menu: Menu
