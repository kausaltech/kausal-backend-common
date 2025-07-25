from collections.abc import Sequence

from django.forms.forms import Form
from django.http.request import HttpRequest
from django_stubs_ext import StrOrPromise
from wagtail.admin.widgets.button import Button

def render(message: StrOrPromise, buttons: Sequence[Button] | None, detail: str = '') -> str: ...
def debug(
    request: HttpRequest, message: StrOrPromise, buttons: Sequence[Button] | None = None, extra_tags: str = ''
) -> None: ...
def info(request: HttpRequest, message: StrOrPromise, buttons: Sequence[Button] | None = None, extra_tags: str = '') -> None: ...
def success(
    request: HttpRequest, message: StrOrPromise, buttons: Sequence[Button] | None = None, extra_tags: str = ''
) -> None: ...
def warning(
    request: HttpRequest, message: StrOrPromise, buttons: Sequence[Button] | None = None, extra_tags: str = ''
) -> None: ...
def error(
    request: HttpRequest, message: StrOrPromise, buttons: Sequence[Button] | None = None, extra_tags: str = ''
) -> None: ...
def validation_error(
    request: HttpRequest, message: StrOrPromise, form: Form, buttons: Sequence[Button] | None = None
) -> None: ...
def button(url: str, text: StrOrPromise, new_window: bool = False) -> tuple[str, StrOrPromise, bool]: ...
