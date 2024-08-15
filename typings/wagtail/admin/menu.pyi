from typing import TypedDict, Unpack

from django.forms.widgets import MediaDefiningClass
from django.http import HttpRequest
from django.utils.functional import cached_property as cached_property
from django_stubs_ext import StrOrPromise
from wagtail import hooks as hooks
from wagtail.admin.ui.sidebar import MenuItem as SidebarMenuItem
from wagtail.coreutils import cautious_slugify as cautious_slugify
from wagtail.utils.deprecation import RemovedInWagtail70Warning as RemovedInWagtail70Warning

from _typeshed import Incomplete

class MenuItemInit(TypedDict, total=False):
    classname: str
    icon_name: str
    name: str
    attrs: dict[str, str]
    order: int


class MenuItem(metaclass=MediaDefiningClass):
    label: StrOrPromise
    url: str
    classname: str
    icon_name: str
    name: str
    attrs: dict[str, str]
    order: int | None
    def __init__(self, label: StrOrPromise, url: str, **kwargs: Unpack[MenuItemInit]) -> None: ...
    def is_shown(self, request: HttpRequest) -> bool:
        """
        Whether this menu item should be shown for the given request; permission
        checks etc should go here. By default, menu items are shown all the time
        """
    def is_active(self, request: HttpRequest) -> bool: ...
    def render_component(self, request: HttpRequest) -> SidebarMenuItem: ...

class DismissibleMenuItemMixin:
    def __init__(self, *args, **kwargs) -> None: ...
    def render_component(self, request: HttpRequest) -> SidebarMenuItem: ...

class DismissibleMenuItem(DismissibleMenuItemMixin, MenuItem): ...

class Menu:
    register_hook_name: Incomplete
    construct_hook_name: Incomplete
    initial_menu_items: Incomplete
    def __init__(self, register_hook_name: Incomplete | None = None, construct_hook_name: Incomplete | None = None, items: Incomplete | None = None) -> None: ...
    @cached_property
    def registered_menu_items(self): ...
    def menu_items_for_request(self, request): ...
    def active_menu_items(self, request): ...
    @property
    def media(self): ...
    def render_component(self, request): ...

class SubmenuMenuItem(MenuItem):
    """A MenuItem which wraps an inner Menu object"""
    menu: Incomplete
    def __init__(self, label, menu, **kwargs) -> None: ...
    def is_shown(self, request): ...
    def is_active(self, request): ...
    def render_component(self, request): ...

class DismissibleSubmenuMenuItem(DismissibleMenuItemMixin, SubmenuMenuItem): ...

class AdminOnlyMenuItem(MenuItem):
    """A MenuItem which is only shown to superusers"""
    def is_shown(self, request): ...

class WagtailMenuRegisterable:
    menu_icon: str
    menu_label: StrOrPromise
    menu_name: str
    menu_order: int
    menu_url: str
    add_to_admin_menu: bool
    add_to_settings_menu: bool
    menu_item_class: type[MenuItem]
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
    items: Incomplete
    menu_icon: str
    add_to_admin_menu: bool
    registerables: Incomplete
    def __init__(self) -> None:
        """
        When initialising, instantiate the classes (or use the instances)
        within 'items', and assign the list to a ``registerables`` attribute.
        """
    def get_submenu_items(self): ...
    def get_menu_item(self, order: Incomplete | None = None): ...

admin_menu: Incomplete
settings_menu: Incomplete
reports_menu: Incomplete
help_menu: Incomplete
