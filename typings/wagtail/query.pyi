from typing import Self, Sequence, Type, TypeVar

from django.db.models import Model, Q
from django.db.models.query import BaseIterable, ModelIterable, QuerySet
from treebeard.mp_tree import MP_Node
from wagtail.models import Page as Page
from wagtail.models.sites import Site as Site
from wagtail.search.queryset import SearchableQuerySetMixin as SearchableQuerySetMixin

M = TypeVar('M', bound=MP_Node)

class TreeQuerySet(QuerySet[M]):
    def descendant_of_q(self, other: M, inclusive: bool = ...) -> Q: ...
    def descendant_of(self, other: M, inclusive: bool = ...) -> Self: ...
    def not_descendant_of(self, other: M, inclusive: bool = ...): ...
    def child_of_q(self, other: M) -> Q: ...
    def child_of(self, other: M) -> Self: ...
    def not_child_of(self, other: M): ...
    def ancestor_of_q(self, other: M, inclusive: bool = ...): ...
    def ancestor_of(self, other: M, inclusive: bool = ...) -> Self: ...
    def not_ancestor_of(self, other: M, inclusive: bool = ...): ...
    def parent_of_q(self, other: M): ...
    def parent_of(self, other: M): ...
    def not_parent_of(self, other: M): ...
    def sibling_of_q(self, other: M, inclusive: bool = ...): ...
    def sibling_of(self, other: M, inclusive: bool = ...): ...
    def not_sibling_of(self, other: M, inclusive: bool = ...): ...


class SpecificQuerySetMixin:
    def specific(self, defer: bool = ...): ...


P = TypeVar('P', bound=Page)


class PageQuerySet(SearchableQuerySetMixin, SpecificQuerySetMixin, TreeQuerySet[P]):
    def live_q(self) -> Self: ...
    def live(self) -> Self: ...
    def not_live(self) -> Self: ...
    def in_menu_q(self) -> Q: ...
    def in_menu(self) -> Self: ...
    def not_in_menu(self) -> Self: ...
    def page_q(self, other: Page) -> Q: ...
    def page(self, other: Page) -> Self: ...
    def not_page(self, other: Page) -> Self: ...
    def type_q(self, *types: Sequence[type[Page]]) -> Q: ...
    def type(self, *types: Sequence[type[Page]]) -> Self: ...
    def not_type(self, *types: Sequence[type[Page]]) -> Self: ...
    def exact_type_q(self, *types: Sequence[type[Page]]) -> Q: ...
    def exact_type(self, *types: Sequence[type[Page]]) -> Self: ...
    def not_exact_type(self, *types: Sequence[type[Page]]) -> Self: ...
    def private_q(self) -> Q: ...
    def public(self) -> Self: ...
    def not_public(self) -> Self: ...
    def private(self) -> Self: ...
    def first_common_ancestor(self, include_self: bool = ..., strict: bool = ...) -> Page: ...
    def unpublish(self) -> None: ...
    def defer_streamfields(self) -> Self: ...
    def in_site(self, site) -> Self: ...
    def translation_of_q(self, page: P, inclusive: bool) -> Q: ...
    def translation_of(self, page, inclusive: bool = ...) -> Self: ...
    def not_translation_of(self, page, inclusive: bool = ...) -> Self: ...
    def prefetch_workflow_states(self): ...
    def annotate_approved_schedule(self): ...
    def annotate_site_root_state(self): ...

class SpecificIterable(BaseIterable):
    def __iter__(self): ...

class DeferredSpecificIterable(ModelIterable):
    def __iter__(self): ...
