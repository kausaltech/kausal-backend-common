from collections.abc import Callable
from typing import Any, ClassVar

from django.http.response import HttpResponseBase
from django.urls import URLPattern
from django.utils.functional import cached_property
from django.views import View
from wagtail.admin.menu import WagtailMenuRegisterable, WagtailMenuRegisterableGroup

class ViewSet(WagtailMenuRegisterable):
    name: ClassVar[str | None]
    icon: ClassVar[str]
    UNDEFINED: ClassVar[object]

    def __init__(self, name: str | None = None, **kwargs: Any) -> None: ...
    url_prefix: cached_property[str] | str
    url_namespace: cached_property[str] | str
    def get_common_view_kwargs(self, **kwargs: Any) -> dict[str, Any]: ...
    def construct_view[ResponseT: HttpResponseBase](
        self, view_class: type[View[ResponseT]], **kwargs: Any
    ) -> Callable[..., ResponseT]: ...
    def inject_view_methods[ViewT: View](self, view_class: type[ViewT], method_names: list[str]) -> type[ViewT]: ...
    def on_register(self) -> None: ...
    def get_urlpatterns(self) -> list[URLPattern]: ...
    def get_url_name(self, view_name: str) -> str: ...

class ViewSetGroup(WagtailMenuRegisterableGroup):
    def on_register(self) -> None: ...
