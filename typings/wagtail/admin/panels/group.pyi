from collections.abc import Sequence
from typing import Any, Generic, TypedDict, TypeVar, Unpack, type_check_only

from django.forms import Media
from django.utils.functional import cached_property as cached_property

from .base import _FC, Panel as Panel, PanelInitArgs, _BPModel, _Model, _Panel_Form

@type_check_only
class PanelGroupOwnInitArgs(TypedDict, total=False):
    permission: str


@type_check_only
class PanelGroupInitArgs(PanelInitArgs, PanelGroupOwnInitArgs): ...


_PPanel_co = TypeVar('_PPanel_co', bound=PanelGroup, covariant=True)


class PanelGroup(Panel[_Model, _Panel_Form]):
    """
    Abstract class for panels that manage a set of sub-panels.
    Concrete subclasses must attach a 'children' property
    """
    children: Sequence[Panel[Any]]
    permission: str | None

    def __init__(self, children: Sequence[Panel[Any]] = (), *args, **kwargs: Unpack[PanelGroupInitArgs]) -> None: ...
    @cached_property
    def child_identifiers(self) -> list[str]:
        """
        A list of identifiers corresponding to child panels in ``self.children``, formed from the clean_name property
        but validated to be unique and non-empty.
        """

    class BoundPanel(Generic[_PPanel_co, _FC, _BPModel], Panel.BoundPanel[_PPanel_co, _FC, _BPModel]):
        template_name: str

        @cached_property
        def children(self) -> list[Panel.BoundPanel[Panel[Any], _FC, _BPModel]]: ...
        @cached_property
        def visible_children(self) -> list[Panel.BoundPanel[Panel[Any], _FC, _BPModel]]: ...
        @cached_property
        def visible_children_with_identifiers(self) -> list[Panel.BoundPanel[Panel[Any], _FC, _BPModel]]: ...
        def show_panel_furniture(self) -> bool: ...
        @property
        def media(self) -> Media: ...


class TabbedInterface(PanelGroup[_Model, _Panel_Form]):
    class BoundPanel(Generic[_PPanel_co, _FC, _BPModel], Panel.BoundPanel[_PPanel_co, _FC, _BPModel]): ...

class ObjectList(PanelGroup[_Model, _Panel_Form]):
    class BoundPanel(Generic[_PPanel_co, _FC, _BPModel], Panel.BoundPanel[_PPanel_co, _FC, _BPModel]): ...

class FieldRowPanel(PanelGroup[_Model, _Panel_Form]):
    class BoundPanel(Generic[_PPanel_co, _FC, _BPModel], Panel.BoundPanel[_PPanel_co, _FC, _BPModel]): ...

class MultiFieldPanel(PanelGroup[_Model, _Panel_Form]):
    class BoundPanel(Generic[_PPanel_co, _FC, _BPModel], Panel.BoundPanel[_PPanel_co, _FC, _BPModel]): ...
