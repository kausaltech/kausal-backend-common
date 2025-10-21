from __future__ import annotations

from typing import TYPE_CHECKING

from wagtail.admin.ui.components import Component as WagtailComponent

if TYPE_CHECKING:
    from laces.typing import RenderContext


class Component(WagtailComponent):
    def get_context_data(self, parent_context: RenderContext) -> RenderContext:  # type: ignore[override]
        return {}
