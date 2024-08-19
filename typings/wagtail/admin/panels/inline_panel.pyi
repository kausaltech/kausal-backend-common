from typing import ClassVar, Generic, Sequence, TypedDict, Unpack, type_check_only
from typing_extensions import TypeVar

from django.db.models import ManyToOneRel, Model
from django.forms import Media
from django.forms.models import BaseModelFormSet, ModelForm
from django.utils.functional import cached_property
from django_stubs_ext import StrOrPromise
from modelcluster.forms import BaseChildFormSet
from wagtail.admin.forms import WagtailAdminModelForm

from .base import Panel, PanelInitArgs, _BPModel, _Model
from .group import MultiFieldPanel

_IPPanel_co = TypeVar('_IPPanel_co', bound=InlinePanel, covariant=True)
_RelatedModel = TypeVar('_RelatedModel', bound=Model, default=Model)
_ChildForm = TypeVar('_ChildForm', bound=ModelForm, default=WagtailAdminModelForm)
_ChildFormSet = TypeVar('_ChildFormSet', bound=BaseModelFormSet, default=BaseChildFormSet)
_ChildModel = TypeVar('_ChildModel', bound=Model, default=Model)


@type_check_only
class InlinePanelOwnInitArgs(TypedDict, total=False):
    panels: Sequence[Panel] | None
    label: StrOrPromise
    min_num: int | None
    max_num: int | None


@type_check_only
class InlinePanelAllInitArgs(PanelInitArgs, InlinePanelOwnInitArgs): ...



class InlinePanel(Generic[_Model, _RelatedModel], Panel[_Model]):
    relation_name: str
    panels: Sequence[Panel[_RelatedModel]] | None
    label: StrOrPromise
    min_num: int | None
    max_num: int | None

    def __init__(
        self,
        relation_name: str,
        **kwargs: Unpack[InlinePanelAllInitArgs],
    ) -> None: ...

    @cached_property
    def panel_definitions(self) -> Sequence[Panel[_RelatedModel]]: ...

    @cached_property
    def child_edit_handler(self) -> MultiFieldPanel[_RelatedModel]: ...

    @property
    def db_field(self) -> ManyToOneRel: ...

    class BoundPanel(
        Generic[_IPPanel_co, _ChildForm, _ChildFormSet, _ChildModel, _BPModel],
        Panel.BoundPanel[_IPPanel_co, _ChildForm, _ChildModel],
    ):
        template_name: ClassVar[str]
        panel: _IPPanel_co
        formset: _ChildFormSet
        label: StrOrPromise
        children: Sequence[Panel.BoundPanel[_IPPanel_co, _ChildForm, _ChildModel]]
        empty_child: Panel.BoundPanel[MultiFieldPanel, _ChildForm, _ChildModel]

        @property
        def media(self) -> Media: ...
