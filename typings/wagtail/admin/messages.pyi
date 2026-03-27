from collections.abc import Sequence

from django.forms.forms import Form
from django.http.request import HttpRequest
from django_stubs_ext import StrOrPromise
from wagtail.admin.widgets.button import Button

type MessageButton = Button | tuple[str, StrOrPromise, bool]

def render(message: StrOrPromise, buttons: Sequence[MessageButton] | None, detail: str = '') -> str: ...
def debug(
    request: HttpRequest, message: StrOrPromise, buttons: Sequence[MessageButton] | None = None, extra_tags: str = ''
) -> None: ...
def info(
    request: HttpRequest, message: StrOrPromise, buttons: Sequence[MessageButton] | None = None, extra_tags: str = ''
) -> None: ...
def success(
    request: HttpRequest, message: StrOrPromise, buttons: Sequence[MessageButton] | None = None, extra_tags: str = ''
) -> None: ...
def warning(
    request: HttpRequest, message: StrOrPromise, buttons: Sequence[MessageButton] | None = None, extra_tags: str = ''
) -> None: ...
def error(
    request: HttpRequest, message: StrOrPromise, buttons: Sequence[MessageButton] | None = None, extra_tags: str = ''
) -> None: ...
def validation_error(
    request: HttpRequest, message: StrOrPromise, form: Form, buttons: Sequence[MessageButton] | None = None
) -> None: ...
def button[TextT: StrOrPromise](url: str, text: TextT, new_window: bool = False) -> tuple[str, TextT, bool]: ...
