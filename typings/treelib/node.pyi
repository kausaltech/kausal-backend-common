from _typeshed import Incomplete

from .exceptions import NodePropertyError as NodePropertyError
from .misc import deprecated as deprecated

class Node:
    ADD: Incomplete
    DELETE: Incomplete
    INSERT: Incomplete
    REPLACE: Incomplete
    expanded: Incomplete
    data: Incomplete
    def __init__(self, tag: Incomplete | None = None, identifier: Incomplete | None = None, expanded: bool = True, data: Incomplete | None = None) -> None: ...
    def __lt__(self, other): ...
    def set_initial_tree_id(self, tree_id) -> None: ...
    @property
    def bpointer(self): ...
    @bpointer.setter
    def bpointer(self, value) -> None: ...
    def update_bpointer(self, nid) -> None: ...
    @property
    def fpointer(self): ...
    @fpointer.setter
    def fpointer(self, value) -> None: ...
    def update_fpointer(self, nid, mode=..., replace: Incomplete | None = None) -> None: ...
    def predecessor(self, tree_id): ...
    def set_predecessor(self, nid, tree_id) -> None: ...
    def successors(self, tree_id): ...
    def set_successors(self, value, tree_id: Incomplete | None = None): ...
    def update_successors(self, nid, mode=..., replace: Incomplete | None = None, tree_id: Incomplete | None = None): ...

    @property
    def identifier(self): ...
    @identifier.setter
    def identifier(self, value) -> None: ...

    def clone_pointers(self, former_tree_id, new_tree_id) -> None: ...
    def reset_pointers(self, tree_id) -> None: ...
    def is_leaf(self, tree_id: Incomplete | None = None): ...
    def is_root(self, tree_id: Incomplete | None = None): ...
    @property
    def tag(self): ...
    @tag.setter
    def tag(self, value) -> None: ...
