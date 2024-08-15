from collections.abc import Sequence
from typing import Any, ClassVar, Generic, Protocol, Self, TypedDict, Unpack, overload, type_check_only
from typing_extensions import TypeVar

from django.db.models import Model
from django.forms import ModelForm
from django.http import HttpRequest
from django.utils.safestring import SafeString
from django_stubs_ext import StrOrPromise
from wagtail.admin.forms.models import (
    WagtailAdminDraftStateFormMixin as WagtailAdminDraftStateFormMixin,
    WagtailAdminModelForm as WagtailAdminModelForm,
)
from wagtail.admin.ui.components import Component as Component
from wagtail.blocks import StreamValue as StreamValue
from wagtail.coreutils import safe_snake_case as safe_snake_case
from wagtail.models import DraftStateMixin as DraftStateMixin
from wagtail.rich_text import RichText as RichText
from wagtail.utils.text import text_from_html as text_from_html

class PanelComparison[Obj](Protocol):
    is_field: bool
    is_child_relation: bool

    def __init__(self, obj_a: Obj, obj_b: Obj): ...
    def has_changed(self) -> bool: ...


_FC = TypeVar('_FC', bound=ModelForm, default=ModelForm)

@overload
def get_form_for_model[M: Model](model: type[M], **kwargs) -> type[WagtailAdminModelForm[M]]: ...

@overload
def get_form_for_model[FormT: ModelForm](model: type[Model], form_class: type[FormT], **kwargs) -> type[FormT]:
    """
    Construct a ModelForm subclass using the given model and base form class. Any additional
    keyword arguments are used to populate the form's Meta class.
    """


type PanelContext = dict[str, Any]

_Model = TypeVar('_Model', bound=Model, default=Model)
_Panel_co = TypeVar('_Panel_co', bound=Panel, covariant=True)
_BPModel = TypeVar('_BPModel', bound=Model, default=Model)
_Panel_Form = TypeVar('_Panel_Form', bound=ModelForm, default=WagtailAdminModelForm)
_BPPanel_Form = TypeVar('_BPPanel_Form', bound=ModelForm, default=WagtailAdminModelForm)

@type_check_only
class PanelInitArgs[F: ModelForm](TypedDict, total=False):
    heading: StrOrPromise
    classname: str
    help_text: StrOrPromise
    base_form_class: type[F]
    icon: str
    attrs: dict[str, str]


class Panel(Generic[_Model, _Panel_Form]):
    """
    Defines part (or all) of the edit form interface for pages and other models
    within the Wagtail admin. Each model has an associated top-level panel definition
    (also known as an edit handler), consisting of a nested structure of ``Panel`` objects.
    This provides methods for obtaining a :class:`~django.forms.ModelForm` subclass,
    with the field list and other parameters collated from all panels in the structure.
    It then handles rendering that form as HTML.

    The following parameters can be used to customise how the panel is displayed.
    For more details, see :ref:`customising_panels`.

    :param heading: The heading text to display for the panel.
    :param classname: A CSS class name to add to the panel's HTML element.
    :param help_text: Help text to display within the panel.
    :param base_form_class: The base form class to use for the panel. Defaults to the model's ``base_form_class``, before falling back to :class:`~wagtail.admin.forms.WagtailAdminModelForm`. This is only relevant for the top-level panel.
    :param icon: The name of the icon to display next to the panel heading.
    :param attrs: A dictionary of HTML attributes to add to the panel's HTML element.
    """
    BASE_ATTRS: ClassVar[dict[str, str]]
    heading: StrOrPromise
    classname: str
    help_text: StrOrPromise
    base_form_class: type[WagtailAdminModelForm] | None
    icon: str
    model: type[_Model] | None
    attrs: dict[str, str]

    def __init__(
        self, **kwargs: Unpack[PanelInitArgs[_Panel_Form]],
    ) -> None: ...

    def clone(self) -> Self:
        """
        Create a clone of this panel definition. By default, constructs a new instance, passing the
        keyword arguments returned by ``clone_kwargs``.
        """
    def clone_kwargs(self) -> dict[str, Any]:
        """
        Return a dictionary of keyword arguments that can be used to create a clone of this panel definition.
        """
    def get_form_options(self) -> dict[str, Any]:
        """
        Return a dictionary of attributes such as 'fields', 'formsets' and 'widgets'
        which should be incorporated into the form class definition to generate a form
        that this panel can use.
        This will only be called after binding to a model (i.e. self.model is available).
        """
    def get_form_class(self) -> type[WagtailAdminModelForm]:
        """
        Construct a form class that has all the fields and formsets named in
        the children of this edit handler.
        """
    def bind_to_model(self, model: type[_Model]) -> Self:
        """
        Create a clone of this panel definition with a ``model`` attribute pointing to the linked model class.
        """
    def get_bound_panel(
        self,
        instance: _Model | None = None,
        request: HttpRequest | None = None,
        form: _Panel_Form | None = None,
        prefix: str = 'panel',
    ) -> Panel.BoundPanel[Panel, _Panel_Form, _Model]:
        """
        Return a ``BoundPanel`` instance that can be rendered onto the template as a component. By default, this creates an instance
        of the panel class's inner ``BoundPanel`` class, which must inherit from ``Panel.BoundPanel``.
        """
    def on_model_bound(self) -> None:
        """
        Called after the panel has been associated with a model class and the ``self.model`` attribute is available;
        panels can override this method to perform additional initialisation related to the model.
        """
    def classes(self) -> list[str]:
        """
        Additional CSS classnames to add to whatever kind of object this is at output.
        Subclasses of Panel should override this, invoking super().classes() to
        append more classes specific to the situation.
        """
    def id_for_label(self) -> str:
        """
        The ID to be used as the 'for' attribute of any <label> elements that refer
        to this object but are rendered outside of it. Leave blank if this object does not render
        as a single input field.
        """
    @property
    def clean_name(self) -> str:
        """
        A name for this panel, consisting only of ASCII alphanumerics and underscores, suitable for use in identifiers.
        Usually generated from the panel heading. Note that this is not guaranteed to be unique or non-empty; anything
        making use of this and requiring uniqueness should validate and modify the return value as needed.
        """
    def format_value_for_display(self, value: Any):
        """
        Hook to allow formatting of raw field values (and other attribute values) for human-readable
        display. For example, if rendering a ``RichTextField`` value, you might extract text from the HTML
        to generate a safer display value.
        """

    class BoundPanel(Generic[_Panel_co, _BPPanel_Form, _BPModel], Component):
        """
        A template component for a panel that has been associated with a model instance, form, and request.
        """
        panel: _Panel_co
        instance: _BPModel
        request: HttpRequest
        form: _BPPanel_Form
        prefix: str
        heading: StrOrPromise
        help_text: StrOrPromise
        def __init__(self, panel: _Panel_co, instance: _Model, request: HttpRequest, form: _FC, prefix: str) -> None: ...
        @property
        def classname(self): ...
        @property
        def attrs(self) -> dict[str, str]: ...
        @property
        def icon(self) -> str | None: ...
        def id_for_label(self) -> str:
            """
            Returns an HTML ID to be used as the target for any label referencing this panel.
            """
        def is_shown(self) -> bool:
            """
            Whether this panel should be rendered; if false, it is skipped in the template output.
            """
        def show_panel_furniture(self) -> bool:
            """
            Whether this panel shows the panel furniture instead of being rendered outside of it.
            """
        def is_required(self) -> bool: ...
        def get_context_data(self, parent_context: PanelContext | None = None) -> PanelContext: ...
        def get_comparison(self) -> Sequence[PanelComparison]: ...
        def render_missing_fields(self) -> str | SafeString:
            '''
            Helper function: render all of the fields that are defined on the form but not "claimed" by
            any panels via required_fields. These fields are most likely to be hidden fields introduced
            by the forms framework itself, such as ORDER / DELETE fields on formset members.
            (If they aren\'t actually hidden fields, then they will appear as ugly unstyled / label-less fields
            outside of the panel furniture. But there\'s not much we can do about that.)
            '''
        def render_form_content(self) -> str | SafeString:
            """
            Render this as an 'object', ensuring that all fields necessary for a valid form
            submission are included
            """
