from typing import Any, ClassVar, Final, Generic, Literal, TypedDict, Unpack, type_check_only
from typing_extensions import TypeVar

from django.db.models import Field
from django.forms import Widget
from django.forms.boundfield import BoundField
from django.utils.functional import cached_property as cached_property

from .base import _FC, Panel, PanelContext, PanelInitArgs as PanelInitArgs, _BPModel, _Model

type WidgetOverrideType = Widget | type[Widget]

@type_check_only
class FieldPanelOwnInitArgs(TypedDict, total=False):
    widget: WidgetOverrideType | None
    disable_comments: bool | None
    permission: str | None
    read_only: bool


@type_check_only
class FieldPanelInitArgs(PanelInitArgs[Any], FieldPanelOwnInitArgs): ...


_FPanel_co = TypeVar('_FPanel_co', bound=FieldPanel, covariant=True)
_DB_field = TypeVar('_DB_field', bound=Field, default=Field)


class FieldPanel(Panel[_Model], Generic[_Model, _DB_field]):
    TEMPLATE_VAR: Final[Literal['field_panel']]
    read_only_output_template_name: str
    field_name: str
    widget: WidgetOverrideType | None
    disable_comments: bool | None
    permission: str | None
    read_only: bool
    model: type[_Model]

    def __init__(
        self, field_name: str, **kwargs: Unpack[FieldPanelInitArgs],
    ) -> None: ...

    @cached_property
    def db_field(self) -> Field: ...
    @property
    def clean_name(self) -> str: ...

    def format_value_for_display(self, value: Any) -> str:
        """
        Overrides ``Panel.format_value_for_display()`` to add additional treatment
        for choice fields.
        """

    class BoundPanel(Panel.BoundPanel[_FPanel_co, _FC, _BPModel], Generic[_FPanel_co, _FC, _BPModel]):
        panel: _FPanel_co
        default_field_icons: ClassVar[dict[str, str]]
        bound_field: BoundField
        read_only: bool

        def __init__(self, **kwargs) -> None: ...
        @property
        def field_name(self) -> str: ...
        @property
        def comments_enabled(self) -> bool: ...
        @cached_property
        def value_from_instance(self) -> Any: ...
        def get_editable_context_data(self) -> PanelContext: ...
        def get_read_only_context_data(self) -> PanelContext: ...
