"""Mixins for Wagtail admin UI views."""
from __future__ import annotations


class HideSnippetsFromBreadcrumbsMixin:
    """Hide access to snippets index view from view breadcrumbs."""

    def get_breadcrumbs_items(self) -> list[dict]:
        breadcrumb_items = super().get_breadcrumbs_items()  # type: ignore
        breadcrumb_items = [item for item in breadcrumb_items if item['label'] != 'Snippets']
        return breadcrumb_items
