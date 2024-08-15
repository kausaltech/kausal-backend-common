from typing import Any, ClassVar, Final, Generic, Literal, TypedDict, Unpack, type_check_only

from django.db.models import Field
from django.forms import Widget
from django.forms.boundfield import BoundField
from django.utils.functional import cached_property as cached_property

from typing_extensions import TypeVar

from .base import _FC, Panel, PanelContext, PanelInitArgs as PanelInitArgs, _BPModel, _Model, _Req

@type_check_only
class FieldPanelOwnInitArgs(TypedDict, total=False):
    widget: Widget | type[Widget] | None
    disable_comments: bool | None
    permission: str | None
    read_only: bool


@type_check_only
class FieldPanelInitArgs(PanelInitArgs, FieldPanelOwnInitArgs): ...


_FPanel_co = TypeVar('_FPanel_co', bound=FieldPanel, covariant=True)
_FPanel_field = TypeVar('_FPanel_field', bound=Field, default=Field)


class FieldPanel(Generic[_Model, _FPanel_field], Panel[_Model]):
    TEMPLATE_VAR: Final[Literal['field_panel']]
    read_only_output_template_name: str
    field_name: str
    widget: Widget | type[Widget] | None
    disable_comments: bool | None
    permission: str | None
    read_only: bool

    def __init__(
        self, field_name: str, **kwargs: Unpack[FieldPanelInitArgs],
    ) -> None: ...

    @cached_property
    def db_field(self) -> Field: ...
    @property
    def clean_name(self) -> str: ...

    def format_value_for_display(self, value: Any) -> str:  # noqa: ANN401
        """
        Overrides ``Panel.format_value_for_display()`` to add additional treatment
        for choice fields.
        """

    class BoundPanel(Generic[_FPanel_co, _FC, _BPModel, _Req], Panel.BoundPanel[_FPanel_co, _FC, _BPModel, _Req]):
        panel: _FPanel_co
        template_name: ClassVar[str]
        default_field_icons: ClassVar[dict[str, str]]
        bound_field: BoundField | None
        read_only: bool

        def __init__(self, **kwargs) -> None: ...
        @property
        def field_name(self) -> str: ...
        @property
        def comments_enabled(self) -> bool: ...
        @cached_property
        def value_from_instance(self) -> Any: ...  # noqa: ANN401
        def get_editable_context_data(self) -> PanelContext: ...
        def get_read_only_context_data(self) -> PanelContext: ...
