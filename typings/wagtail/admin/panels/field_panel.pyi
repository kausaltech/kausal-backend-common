from typing import Any, ClassVar, Final, TypedDict, Unpack, type_check_only

from django.db.models import Field, Model
from django.forms import ModelForm, Widget
from django.forms.boundfield import BoundField
from django.utils.functional import cached_property as cached_property

from .base import Panel, PanelContext, PanelInitArgs as PanelInitArgs, WagtailAdminModelForm

type WidgetOverrideType = Widget | type[Widget]

@type_check_only
class FieldPanelOwnInitArgs(TypedDict, total=False):
    widget: WidgetOverrideType | None
    disable_comments: bool | None
    permission: str | None
    read_only: bool

@type_check_only
class FieldPanelInitArgs(PanelInitArgs[Any], FieldPanelOwnInitArgs): ...

class FieldPanel[
    M: Model = Model,
    DBField: Field[Any, Any] = Field[Any, Any],
    FormT: ModelForm[Any] = WagtailAdminModelForm[Any],
](Panel[M, FormT]):
    TEMPLATE_VAR: Final = 'field_panel'
    read_only_output_template_name: str
    field_name: str
    widget: WidgetOverrideType | None
    disable_comments: bool | None
    permission: str | None
    read_only: bool
    model: type[M]

    def __init__(
        self,
        field_name: str,
        **kwargs: Unpack[FieldPanelInitArgs],
    ) -> None: ...
    @cached_property
    def db_field(self) -> DBField: ...
    @property
    def clean_name(self) -> str: ...
    def format_value_for_display(self, value: Any) -> str:
        """
        Overrides ``Panel.format_value_for_display()`` to add additional treatment
        for choice fields.
        """

    class BoundPanel[ParentPanel: FieldPanel[Any, Any] = FieldPanel[Model, Any]](Panel.BoundPanel[ParentPanel, Any, Model]):
        panel: ParentPanel
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
