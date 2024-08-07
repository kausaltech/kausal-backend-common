from typing import Any, Callable, ClassVar, Dict, List, Optional, Type

from django.http.response import HttpResponseBase
from django.urls import URLPattern
from django.views import View
from wagtail.admin.menu import WagtailMenuRegisterable, WagtailMenuRegisterableGroup

class ViewSet(WagtailMenuRegisterable):
    name: ClassVar[str | None]
    icon: ClassVar[str]
    url_prefix: ClassVar[str]
    url_namespace: ClassVar[str]
    menu_icon: ClassVar[str]
    menu_url: ClassVar[str]

    def __init__(self, name: str | None = None, **kwargs: Any) -> None: ...
    def get_common_view_kwargs(self, **kwargs: Any) -> dict[str, Any]: ...
    def construct_view(self, view_class: type[View], **kwargs: Any) -> Callable[..., HttpResponseBase]: ...
    def inject_view_methods(self, view_class: type[View], method_names: list[str]) -> type[View]: ...
    def on_register(self) -> None: ...
    def get_urlpatterns(self) -> list[URLPattern]: ...
    def get_url_name(self, view_name: str) -> str: ...

class ViewSetGroup(WagtailMenuRegisterableGroup):
    def on_register(self) -> None: ...
