from typing import Generic, Literal, Self, TypeVar

from _typeshed import Incomplete
from django.db.models import Model, QuerySet

M = TypeVar('M', bound=Model, default=Model)
QS = TypeVar('QS', bound=QuerySet[Model], default=QuerySet[Model])


class Node(Model, Generic[M, QS]):
    @classmethod
    def add_root(cls, **kwargs) -> M: ...
    @classmethod
    def get_foreign_keys(cls): ...
    @classmethod
    def load_bulk(cls, bulk_data, parent: Incomplete | None = ..., keep_ids: bool = ...): ...
    @classmethod
    def dump_bulk(cls, parent: Incomplete | None = ..., keep_ids: bool = ...) -> None: ...
    @classmethod
    def get_root_nodes(cls) -> QuerySet[Self]: ...
    @classmethod
    def get_first_root_node(cls) -> Self | None: ...
    @classmethod
    def get_last_root_node(cls) -> Self | None: ...
    @classmethod
    def find_problems(cls) -> None: ...
    @classmethod
    def fix_tree(cls) -> None: ...
    @classmethod
    def get_tree(cls, parent: Self | None = ...) -> QuerySet[Self]: ...
    @classmethod
    def get_descendants_group_count(cls, parent: Self | None = ...) -> list[Self]: ...
    def get_depth(self) -> int: ...
    def get_siblings(self) -> QuerySet[Self]: ...
    def get_children(self) -> QS: ...
    def get_children_count(self) -> int: ...
    def get_descendants(self) -> QuerySet[Self]: ...
    def get_descendant_count(self) -> int: ...
    def get_first_child(self) -> Self | None: ...
    def get_last_child(self) -> Self | None: ...
    def get_first_sibling(self) -> Self | None: ...
    def get_last_sibling(self) -> Self | None: ...
    def get_prev_sibling(self) -> Self | None: ...
    def get_next_sibling(self) -> Self | None: ...
    def is_sibling_of(self, node: Self) -> bool: ...
    def is_child_of(self, node: Self) -> bool: ...
    def is_descendant_of(self, node: Self) -> bool: ...
    def add_child(self, **kwargs) -> Self: ...
    def add_sibling(self, pos: Literal['first-sibling', 'left', 'right', 'last-sibling', 'sorted-sibling'] | None = ..., **kwargs) -> Self: ...
    def get_root(self) -> Self: ...
    def is_root(self) -> bool: ...
    def is_leaf(self) -> bool: ...
    def get_ancestors(self) -> QuerySet[Self]: ...
    def get_parent(self, update: bool = ...) -> Self | None: ...
    def move(self, target: Self, pos: str | None = ...) -> None: ...
    def get_sorted_pos_queryset(self, siblings, newobj): ...
    @classmethod
    def get_annotated_list_qs(cls, qs) -> list: ...
    @classmethod
    def get_annotated_list(cls, parent: Self | None = ..., max_depth: int | None = ...) -> list: ...
