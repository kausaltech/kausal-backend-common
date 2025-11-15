from typing import Any, Literal, Self, TypedDict, Unpack, overload

from django.db.models import Model, QuerySet

from treebeard.exceptions import InvalidPosition as InvalidPosition, MissingNodeOrderBy as MissingNodeOrderBy

class _InstanceKwargs[M: Model](TypedDict, total=True):
    instance: M

class Node[QS: QuerySet[Any]](Model):
    """Node class"""

    @overload
    @classmethod
    def add_root(cls, **kwargs: Unpack[_InstanceKwargs[Self]]) -> Self: ...

    @overload
    @classmethod
    def add_root(cls, **kwargs) -> Self:
        """
        Adds a root node to the tree. The new root node will be the new
        rightmost root node. If you want to insert a root node at a specific
        position, use :meth:`add_sibling` in an already existing root node
        instead.

        :param `**kwargs`: object creation data that will be passed to the
            inherited Node model
        :param instance: Instead of passing object creation data, you can
            pass an already-constructed (but not yet saved) model instance to
            be inserted into the tree.

        :returns: the created node object. It will be save()d by this method.

        :raise NodeAlreadySaved: when the passed ``instance`` already exists
            in the database
        """
    @classmethod
    def get_foreign_keys(cls) -> dict[str, type[Model]]:
        """Get foreign keys and models they refer to, so we can pre-process
        the data for load_bulk
        """
    @classmethod
    def load_bulk(cls, bulk_data, parent: Self | None = None, keep_ids: bool = False) -> list[Any]:
        """
        Loads a list/dictionary structure to the tree.


        :param bulk_data:

            The data that will be loaded, the structure is a list of
            dictionaries with 2 keys:

            - ``data``: will store arguments that will be passed for object
              creation, and

            - ``children``: a list of dictionaries, each one has it's own
              ``data`` and ``children`` keys (a recursive structure)


        :param parent:

            The node that will receive the structure as children, if not
            specified the first level of the structure will be loaded as root
            nodes


        :param keep_ids:

            If enabled, loads the nodes with the same primary keys that are
            given in the structure. Will error if there are nodes without
            primary key info or if the primary keys are already used.


        :returns: A list of the added node ids.
        """
    @classmethod
    def dump_bulk(cls, parent: Self | None = None, keep_ids: bool = True) -> list[dict[str, Any]]:
        """
        Dumps a tree branch to a python data structure.

        :param parent:

            The node whose descendants will be dumped. The node itself will be
            included in the dump. If not given, the entire tree will be dumped.

        :param keep_ids:

            Stores the pk value (primary key) of every node. Enabled by
            default.

        :returns: A python data structure, described with detail in
                  :meth:`load_bulk`
        """
    @classmethod
    def get_root_nodes(cls) -> QS:
        """:returns: A queryset containing the root nodes in the tree."""

    @classmethod
    def get_first_root_node(cls) -> Self | None:
        """
        :returns:

            The first root node in the tree or ``None`` if it is empty.
        """
    @classmethod
    def get_last_root_node(cls) -> Self | None:
        """
        :returns:

            The last root node in the tree or ``None`` if it is empty.
        """
    @classmethod
    def find_problems(cls) -> Any:
        """Checks for problems in the tree structure."""
    @classmethod
    def fix_tree(cls) -> None:
        """
        Solves problems that can appear when transactions are not used and
        a piece of code breaks, leaving the tree in an inconsistent state.
        """
    @classmethod
    def get_tree(cls, parent: Self | None = None) -> QS:
        """
        :returns:

            A list of nodes ordered as DFS, including the parent. If
            no parent is given, the entire tree is returned.
        """
    @classmethod
    def get_descendants_group_count(cls, parent: Self | None = None) -> list[Self]:
        """
        Helper for a very common case: get a group of siblings and the number
        of *descendants* (not only children) in every sibling.

        :param parent:

            The parent of the siblings to return. If no parent is given, the
            root nodes will be returned.

        :returns:

            A `list` (**NOT** a Queryset) of node objects with an extra
            attribute: `descendants_count`.
        """
    def get_depth(self) -> int:
        """:returns: the depth (level) of the node"""
    def get_siblings(self) -> QS:
        """
        :returns:

            A queryset of all the node's siblings, including the node
            itself.
        """
    def get_children(self) -> QS:
        """:returns: A queryset of all the node's children"""
    def get_children_count(self) -> int:
        """:returns: The number of the node's children"""
    def get_descendants(self) -> QS:
        """
        :returns:

            A queryset of all the node's descendants, doesn't
            include the node itself (some subclasses may return a list).
        """
    def get_descendant_count(self) -> int:
        """:returns: the number of descendants of a node."""
    def get_first_child(self) -> Self | None:
        """
        :returns:

            The leftmost node's child, or None if it has no children.
        """
    def get_last_child(self) -> Self | None:
        """
        :returns:

            The rightmost node's child, or None if it has no children.
        """
    def get_first_sibling(self) -> Self | None:
        """
        :returns:

            The leftmost node's sibling, can return the node itself if
            it was the leftmost sibling.
        """
    def get_last_sibling(self) -> Self | None:
        """
        :returns:

            The rightmost node's sibling, can return the node itself if
            it was the rightmost sibling.
        """
    def get_prev_sibling(self) -> Self | None:
        """
        :returns:

            The previous node's sibling, or None if it was the leftmost
            sibling.
        """
    def get_next_sibling(self) -> Self | None:
        """
        :returns:

            The next node's sibling, or None if it was the rightmost
            sibling.
        """
    def is_sibling_of(self, node: Self) -> bool:
        """
        :returns: ``True`` if the node is a sibling of another node given as an
            argument, else, returns ``False``

        :param node:

            The node that will be checked as a sibling
        """
    def is_child_of(self, node: Self) -> bool:
        """
        :returns: ``True`` if the node is a child of another node given as an
            argument, else, returns ``False``

        :param node:

            The node that will be checked as a parent
        """
    def is_descendant_of(self, node: Self) -> bool:
        """
        :returns: ``True`` if the node is a descendant of another node given
            as an argument, else, returns ``False``

        :param node:

            The node that will be checked as an ancestor
        """

    @overload
    def add_child(self, **kwargs: Unpack[_InstanceKwargs[Self]]) -> Self: ...

    @overload
    def add_child(self, **kwargs) -> Self:
        """
        Adds a child to the node. The new node will be the new rightmost
        child. If you want to insert a node at a specific position,
        use the :meth:`add_sibling` method of an already existing
        child node instead.

        :param `**kwargs`:

            Object creation data that will be passed to the inherited Node
            model
        :param instance: Instead of passing object creation data, you can
            pass an already-constructed (but not yet saved) model instance to
            be inserted into the tree.

        :returns: The created node object. It will be save()d by this method.

        :raise NodeAlreadySaved: when the passed ``instance`` already exists
            in the database
        """

    type SiblingPos = Literal['first-sibling', 'left', 'right', 'last-sibling', 'sorted-sibling']

    @overload
    def add_sibling(self, pos: SiblingPos | None = None, **kwargs: _InstanceKwargs[Self]) -> Self: ...

    @overload
    def add_sibling(self, pos: SiblingPos | None = None, **kwargs) -> Self:
        """
        Adds a new node as a sibling to the current node object.


        :param pos:
            The position, relative to the current node object, where the
            new node will be inserted, can be one of:

            - ``first-sibling``: the new node will be the new leftmost sibling
            - ``left``: the new node will take the node's place, which will be
              moved to the right 1 position
            - ``right``: the new node will be inserted at the right of the node
            - ``last-sibling``: the new node will be the new rightmost sibling
            - ``sorted-sibling``: the new node will be at the right position
              according to the value of node_order_by

        :param `**kwargs`:

            Object creation data that will be passed to the inherited
            Node model
        :param instance: Instead of passing object creation data, you can
            pass an already-constructed (but not yet saved) model instance to
            be inserted into the tree.

        :returns:

            The created node object. It will be saved by this method.

        :raise InvalidPosition: when passing an invalid ``pos`` parm
        :raise InvalidPosition: when :attr:`node_order_by` is enabled and the
           ``pos`` parm wasn't ``sorted-sibling``
        :raise MissingNodeOrderBy: when passing ``sorted-sibling`` as ``pos``
           and the :attr:`node_order_by` attribute is missing
        :raise NodeAlreadySaved: when the passed ``instance`` already exists
            in the database
        """
    def get_root(self) -> Self:
        """:returns: the root node for the current node object."""
    def is_root(self) -> bool:
        """:returns: True if the node is a root node (else, returns False)"""
    def is_leaf(self) -> bool:
        """:returns: True if the node is a leaf node (else, returns False)"""
    def get_ancestors(self) -> QS:
        """
        :returns:

            A queryset containing the current node object's ancestors,
            starting by the root node and descending to the parent.
            (some subclasses may return a list)
        """
    def get_parent(self, update: bool = False) -> Self | None:
        """
        :returns: the parent node of the current node object.
            Caches the result in the object itself to help in loops.

        :param update: Updates the cached value.
        """
    type _MovePos = Literal[
        'first-child', 'last-child', 'sorted-child', 'first-sibling', 'left', 'right',
        'last-sibling', 'sorted-sibling',
    ]

    def move(self, target: Self, pos: _MovePos | None = None) -> None:
        """
        Moves the current node and all it's descendants to a new position
        relative to another node.

        :param target:

            The node that will be used as a relative child/sibling when moving

        :param pos:

            The position, relative to the target node, where the
            current node object will be moved to, can be one of:

            - ``first-child``: the node will be the new leftmost child of the
              ``target`` node
            - ``last-child``: the node will be the new rightmost child of the
              ``target`` node
            - ``sorted-child``: the new node will be moved as a child of the
              ``target`` node according to the value of :attr:`node_order_by`
            - ``first-sibling``: the node will be the new leftmost sibling of
              the ``target`` node
            - ``left``: the node will take the ``target`` node's place, which
              will be moved to the right 1 position
            - ``right``: the node will be moved to the right of the ``target``
              node
            - ``last-sibling``: the node will be the new rightmost sibling of
              the ``target`` node
            - ``sorted-sibling``: the new node will be moved as a sibling of
              the ``target`` node according to the value of
              :attr:`node_order_by`

            .. note::

               If no ``pos`` is given the library will use ``last-sibling``,
               or ``sorted-sibling`` if :attr:`node_order_by` is enabled.

        :returns: None

        :raise InvalidPosition: when passing an invalid ``pos`` parm
        :raise InvalidPosition: when :attr:`node_order_by` is enabled and the
           ``pos`` parm wasn't ``sorted-sibling`` or ``sorted-child``
        :raise InvalidMoveToDescendant: when trying to move a node to one of
           it's own descendants
        :raise PathOverflow: when the library can't make room for the
           node's new position
        :raise MissingNodeOrderBy: when passing ``sorted-sibling`` or
           ``sorted-child`` as ``pos`` and the :attr:`node_order_by`
           attribute is missing
        """
    def delete(self, *args, **kwargs) -> tuple[int, dict[str, int]]:
        """Removes a node and all it's descendants."""

    def get_sorted_pos_queryset(self, siblings: QS, newobj: Self):
        """
        :returns:

            A queryset of the nodes that must be moved to the right.
            Called only for Node models with :attr:`node_order_by`

        This function is based on _insertion_target_filters from django-mptt
        (BSD licensed) by Jonathan Buchanan:
        https://github.com/django-mptt/django-mptt/blob/0.3.0/mptt/signals.py
        """
    @classmethod
    def get_annotated_list_qs(cls, qs: QS) -> list[tuple[Self, dict[str, Any]]]:
        """
        Gets an annotated list from a queryset.
        """
    @classmethod
    def get_annotated_list(cls, parent: Self | None = None, max_depth: int | None = None) -> list[tuple[Self, dict[str, Any]]]:
        """
        Gets an annotated list from a tree branch.

        :param parent:

            The node whose descendants will be annotated. The node itself
            will be included in the list. If not given, the entire tree
            will be annotated.

        :param max_depth:

            Optionally limit to specified depth
        """
    @classmethod
    def get_database_vendor(cls, action: Literal['read', 'write']) -> str:
        """
        returns the supported database vendor used by a treebeard model when
        performing read (select) or write (update, insert, delete) operations.

        :param action:

            `read` or `write`

        :returns: postgresql, mysql or sqlite
        """
