from typing import Generic, Self
from typing_extensions import TypeVar

from django.db import models
from django.db.models import Model, Q, QuerySet
from django.db.models.query import BaseIterable, ModelIterable
from wagtail.models import Page
from wagtail.models.sites import Site as Site
from wagtail.search.queryset import SearchableQuerySetMixin as SearchableQuerySetMixin

_NodeT = TypeVar('_NodeT', bound=Model)

class TreeQuerySet(QuerySet[_NodeT, _NodeT]):
    """
    Extends Treebeard's MP_NodeQuerySet with additional useful tree-related operations.
    """
    def delete(self) -> None:  # type: ignore
        """Redefine the delete method unbound, so we can set the queryset_only parameter."""

    def descendant_of_q(self, other, inclusive: bool = False) -> Q: ...
    def descendant_of(self, other, inclusive: bool = False) -> Self:
        """
        This filters the QuerySet to only contain pages that descend from the specified page.

        If inclusive is set to True, it will also contain the page itself (instead of just its descendants).
        """
    def not_descendant_of(self, other, inclusive: bool = False) -> Self:
        """
        This filters the QuerySet to not contain any pages that descend from the specified page.

        If inclusive is set to True, it will also exclude the specified page.
        """
    def child_of_q(self, other) -> Q: ...
    def child_of(self, other) -> Self:
        """
        This filters the QuerySet to only contain pages that are direct children of the specified page.
        """
    def not_child_of(self, other) -> Self:
        """
        This filters the QuerySet to not contain any pages that are direct children of the specified page.
        """
    def ancestor_of_q(self, other, inclusive: bool = False) -> Q: ...
    def ancestor_of(self, other, inclusive: bool = False) -> Self:
        """
        This filters the QuerySet to only contain pages that are ancestors of the specified page.

        If inclusive is set to True, it will also include the specified page.
        """
    def not_ancestor_of(self, other, inclusive: bool = False) -> Self:
        """
        This filters the QuerySet to not contain any pages that are ancestors of the specified page.

        If inclusive is set to True, it will also exclude the specified page.
        """
    def parent_of_q(self, other: _NodeT) -> Q: ...
    def parent_of(self, other: _NodeT) -> Self:
        """
        This filters the QuerySet to only contain the parent of the specified page.
        """
    def not_parent_of(self, other: _NodeT) -> Self:
        """
        This filters the QuerySet to exclude the parent of the specified page.
        """
    def sibling_of_q(self, other: _NodeT, inclusive: bool = True) -> Q: ...
    def sibling_of(self, other: _NodeT, inclusive: bool = True) -> Self:
        """
        This filters the QuerySet to only contain pages that are siblings of the specified page.

        By default, inclusive is set to True so it will include the specified page in the results.

        If inclusive is set to False, the page will be excluded from the results.
        """
    def not_sibling_of(self, other: _NodeT, inclusive: bool = True) -> Self:
        """
        This filters the QuerySet to not contain any pages that are siblings of the specified page.

        By default, inclusive is set to True so it will exclude the specified page from the results.

        If inclusive is set to False, the page will be included in the results.
        """
    @classmethod
    def as_manager(cls) -> TreeManager: ...

class BaseTreeManager(models.Manager[_NodeT]):
    def get_queryset(self) -> TreeQuerySet: ...

class TreeManager(BaseTreeManager): ...

_BaseModelQS = TypeVar('_BaseModelQS', bound=QuerySet, covariant=True)  # noqa: PLC0105

class SpecificQuerySetMixin(Generic[_BaseModelQS]):
    def __init__(self, *args, **kwargs) -> None:
        """Set custom instance attributes"""

    def specific(self, defer: bool = False) -> _BaseModelQS:
        '''
        This efficiently gets all the specific items for the queryset, using
        the minimum number of queries.

        When the "defer" keyword argument is set to True, only generic
        field values will be loaded and all specific fields will be deferred.
        '''
    @property
    def is_specific(self) -> bool:
        """
        Returns True if this queryset is already specific, False otherwise.
        """

_PageT = TypeVar('_PageT', bound=Page, default=Page)


class PageQuerySet(
    Generic[_PageT], SearchableQuerySetMixin, SpecificQuerySetMixin[PageQuerySet[Page]], TreeQuerySet[_PageT],
):
    def live_q(self) -> Q: ...
    def live(self) -> Self:
        """
        This filters the QuerySet to only contain published pages.
        """
    def not_live(self) -> Self:
        """
        This filters the QuerySet to only contain unpublished pages.
        """
    def in_menu_q(self) -> Q: ...
    def in_menu(self) -> Self:
        """
        This filters the QuerySet to only contain pages that are in the menus.
        """
    def not_in_menu(self) -> Self:
        """
        This filters the QuerySet to only contain pages that are not in the menus.
        """
    def page_q(self, other: Page) -> Q: ...
    def page(self, other: Page):
        """
        This filters the QuerySet so it only contains the specified page.
        """
    def not_page(self, other):
        """
        This filters the QuerySet so it doesn't contain the specified page.
        """
    def type_q(self, *types: type[Page]) -> Q: ...
    def type(self, *types: type[Page]) -> Self:
        """
        This filters the QuerySet to only contain pages that are an instance
        of the specified model(s) (including subclasses).
        """
    def not_type(self, *types):
        """
        This filters the QuerySet to exclude any pages which are an instance of the specified model(s).
        """
    def exact_type_q(self, *types) -> Q: ...
    def exact_type(self, *types):
        """
        This filters the QuerySet to only contain pages that are an instance of the specified model(s)
        (matching the model exactly, not subclasses).
        """
    def not_exact_type(self, *types):
        """
        This filters the QuerySet to exclude any pages which are an instance of the specified model(s)
        (matching the model exactly, not subclasses).
        """
    def private_q(self) -> Q: ...
    def public(self):
        """
        Filters the QuerySet to only contain pages that are not in a private
        section and their descendants.
        """
    def not_public(self):
        """
        Filters the QuerySet to only contain pages that are in a private
        section and their descendants.
        """
    def private(self):
        """
        Filters the QuerySet to only contain pages that are in a private
        section and their descendants.
        """
    def first_common_ancestor(self, include_self: bool = False, strict: bool = False):
        """
        Find the first ancestor that all pages in this queryset have in common.
        For example, consider a page hierarchy like::

            - Home/
                - Foo Event Index/
                    - Foo Event Page 1/
                    - Foo Event Page 2/
                - Bar Event Index/
                    - Bar Event Page 1/
                    - Bar Event Page 2/

        The common ancestors for some queries would be:

        .. code-block:: python

            >>> Page.objects\\\n            ...     .type(EventPage)\\\n            ...     .first_common_ancestor()
            <Page: Home>
            >>> Page.objects\\\n            ...     .type(EventPage)\\\n            ...     .filter(title__contains='Foo')\\\n            ...     .first_common_ancestor()
            <Page: Foo Event Index>

        This method tries to be efficient, but if you have millions of pages
        scattered across your page tree, it will be slow.

        If `include_self` is True, the ancestor can be one of the pages in the
        queryset:

        .. code-block:: python

            >>> Page.objects\\\n            ...     .filter(title__contains='Foo')\\\n            ...     .first_common_ancestor()
            <Page: Foo Event Index>
            >>> Page.objects\\\n            ...     .filter(title__exact='Bar Event Index')\\\n            ...     .first_common_ancestor()
            <Page: Bar Event Index>

        A few invalid cases exist: when the queryset is empty, when the root
        Page is in the queryset and ``include_self`` is False, and when there
        are multiple page trees with no common root (a case Wagtail does not
        support). If ``strict`` is False (the default), then the first root
        node is returned in these cases. If ``strict`` is True, then a
        ``ObjectDoesNotExist`` is raised.
        """
    def unpublish(self) -> None:
        """
        This unpublishes all live pages in the QuerySet.
        """
    def defer_streamfields(self):
        """
        Apply to a queryset to prevent fetching/decoding of StreamField values on
        evaluation. Useful when working with potentially large numbers of results,
        where StreamField values are unlikely to be needed. For example, when
        generating a sitemap or a long list of page links.
        """
    def in_site(self, site):
        """
        This filters the QuerySet to only contain pages within the specified site.
        """
    def translation_of_q(self, page, inclusive): ...
    def translation_of(self, page, inclusive: bool = False):
        """
        This filters the QuerySet to only contain pages that are translations of the specified page.

        If inclusive is True, the page itself is returned.
        """
    def not_translation_of(self, page, inclusive: bool = False):
        """
        This filters the QuerySet to only contain pages that are not translations of the specified page.

        Note, this will include the page itself as the page is technically not a translation of itself.
        If inclusive is True, we consider the page to be a translation of itself so this excludes the page
        from the results.
        """
    def prefetch_workflow_states(self):
        """
        Performance optimisation for listing pages.
        Prefetches the active workflow states on each page in this queryset.
        Used by `workflow_in_progress` and `current_workflow_progress` properties on
        `wagtailcore.models.Page`.
        """
    def annotate_approved_schedule(self):
        """
        Performance optimisation for listing pages.
        Annotates each page with the existence of an approved go live time.
        Used by `approved_schedule` property on `wagtailcore.models.Page`.
        """
    def annotate_site_root_state(self):
        """
        Performance optimisation for listing pages.
        Annotates each object with whether it is a root page of any site.
        Used by `is_site_root` method on `wagtailcore.models.Page`.
        """

class SpecificIterable(BaseIterable):
    def __iter__(self):
        """
        Identify and return all specific items in a queryset, and return them
        in the same order, with any annotations intact.
        """

class DeferredSpecificIterable(ModelIterable):
    def __iter__(self): ...
