"""Mixins for Wagtail admin UI views."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

    from wagtail.admin.views.generic.base import BreadcrumbItem


class HideSnippetsFromBreadcrumbsMixin:
    """Hide access to snippets index view from view breadcrumbs."""

    def get_breadcrumbs_items(self) -> Sequence[BreadcrumbItem]:
        breadcrumb_items = super().get_breadcrumbs_items()  # type: ignore
        breadcrumb_items = [item for item in breadcrumb_items if item['label'] != 'Snippets']
        return breadcrumb_items
