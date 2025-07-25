from collections.abc import Callable, Sequence
from typing import Any

from django.utils.functional import cached_property as cached_property
from django_stubs_ext import StrOrPromise
from wagtail import hooks as hooks
from wagtail.admin.ui.components import Component as Component
from wagtail.coreutils import accepts_kwarg as accepts_kwarg
from wagtail.utils.deprecation import RemovedInWagtail70Warning as RemovedInWagtail70Warning

from _typeshed import Incomplete

type ReadOnlyProp[T] = T | Callable[[Any], T]

class Button(Component):
    template_name: str
    show: ReadOnlyProp[bool]
    label: StrOrPromise
    icon_name: str
    url: ReadOnlyProp[str] | None
    attrs: dict[str, Any]
    classname: str
    priority: int

    def __init__(
        self,
        label: str = '',
        url: str | None = None,
        classname: str = '',
        icon_name: Incomplete | None = None,
        attrs={},
        priority: int = 1000,
    ) -> None: ...
    def get_context_data(self, parent_context): ...
    @property
    def base_attrs_string(self): ...
    @property
    def aria_label(self): ...
    def __lt__(self, other): ...
    def __le__(self, other): ...
    def __gt__(self, other): ...
    def __ge__(self, other): ...
    def __eq__(self, other): ...

class HeaderButton(Button):
    """An icon-only button to be displayed after the breadcrumbs in the header."""
    def __init__(
        self,
        label: str = '',
        url: Incomplete | None = None,
        classname: str = '',
        icon_name: Incomplete | None = None,
        attrs={},
        icon_only: bool = False,
        **kwargs,
    ) -> None: ...

class ListingButton(Button):
    def __init__(self, label: StrOrPromise = '', url: str | None = None, classname: str = '', **kwargs) -> None: ...

class PageListingButton(ListingButton):
    aria_label_format: Incomplete
    url_name: Incomplete
    page: Incomplete
    user: Incomplete
    next_url: Incomplete
    def __init__(
        self,
        *args,
        page: Incomplete | None = None,
        next_url: Incomplete | None = None,
        attrs={},
        user: Incomplete | None = None,
        **kwargs,
    ) -> None: ...
    @cached_property
    def page_perms(self): ...

class BaseDropdownMenuButton(Button):
    template_name: str
    def __init__(self, *args, **kwargs) -> None: ...
    @property
    def dropdown_buttons(self) -> Sequence[Button]: ...
    def get_context_data(self, parent_context): ...

class ButtonWithDropdown(BaseDropdownMenuButton):
    dropdown_buttons: Incomplete
    def __init__(self, *args, **kwargs) -> None: ...

class ButtonWithDropdownFromHook(BaseDropdownMenuButton):
    hook_name: Incomplete
    page: Incomplete
    user: Incomplete
    next_url: Incomplete
    def __init__(
        self,
        label,
        hook_name,
        page,
        user: Incomplete | None = None,
        page_perms: Incomplete | None = None,
        next_url: Incomplete | None = None,
        **kwargs,
    ) -> None: ...
    @property
    def dropdown_buttons(self) -> Sequence[Button]: ...
