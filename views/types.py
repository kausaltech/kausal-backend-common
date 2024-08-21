from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Self

from wagtail.admin.ui.components import Component as WagtailComponent

if TYPE_CHECKING:
    from typing import type_check_only

    from django.http import HttpRequest

    from laces.typing import RenderContext

    from users.models import User

    @type_check_only
    class AdminHttpRequest(HttpRequest):
        user: User


class Component(WagtailComponent):
    def get_context_data(self, parent_context: RenderContext) -> RenderContext:
        return {}
