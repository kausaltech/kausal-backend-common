from typing import Any, Callable, Concatenate, Generic, Mapping, ParamSpec, TypeAlias, TypeVar, Unpack
from typing_extensions import TypedDict

from django.contrib.auth.base_user import AbstractBaseUser
from django.db.models import Field as DBField, Model
from django.forms import Field as FormField
from django.forms.models import ModelFormOptions
from django.forms.renderers import BaseRenderer
from django.forms.utils import ErrorList, _DataT, _FilesT
from modelcluster.forms import ClusterForm, ClusterFormMetaclass, ClusterFormOptions
from wagtail.admin import widgets as widgets
from wagtail.admin.forms.tags import TagField as TagField
from wagtail.models import Page as Page
from wagtail.utils.registry import ModelFieldRegistry as ModelFieldRegistry

from permissionedforms import PermissionedForm, PermissionedFormMetaclass, PermissionedFormOptionsMixin  # type: ignore

registry: ModelFieldRegistry

type DBFieldT = type[DBField]

FORM_FIELD_OVERRIDES: dict[DBFieldT, dict]
DIRECT_FORM_FIELD_OVERRIDES: dict[DBFieldT, dict]


def register_form_field_override(
    db_field_class: type[DBField], to: type[Model] | None = None, override: dict[str, Any] = ..., exact_class: bool = False,
) -> None:
    """
    Define parameters for form fields to be used by WagtailAdminModelForm for a given
    database field.
    """

_P = ParamSpec('_P')
FormfieldCallback: TypeAlias = Callable[Concatenate[DBField, _P], FormField]  # noqa: UP040

def formfield_for_dbfield(db_field: DBField, **kwargs: Any) -> FormField: ...

class WagtailAdminModelFormOptions(PermissionedFormOptionsMixin, ClusterFormOptions): ...

class WagtailAdminModelFormMetaclass(PermissionedFormMetaclass, ClusterFormMetaclass):
    options_class: type[ModelFormOptions] = WagtailAdminModelFormOptions
    extra_form_count: int
    @classmethod
    def child_form(cls) -> type[WagtailAdminModelForm]: ...


class BaseModelFormKwargs[M: Model](TypedDict, total=False):
    data: _DataT | None
    files: _FilesT | None
    auto_id: bool | str
    prefix: str | None
    initial: Mapping[str, Any] | None
    error_class: type[ErrorList]
    label_suffix: str | None
    empty_permitted: bool
    instance: M | None
    use_required_attribute: bool | None
    renderer: BaseRenderer | None

_U = TypeVar('_U', bound=AbstractBaseUser, default=AbstractBaseUser, covariant=True)
_M = TypeVar('_M', bound=Model, default=Model)


class WagtailAdminModelForm(
    Generic[_M, _U], PermissionedForm, ClusterForm[_M], metaclass=WagtailAdminModelFormMetaclass,
):
    for_user: _U | None

    def __init__(self, *args, for_user: _U | None = ..., **kwargs: Unpack[BaseModelFormKwargs[_M]]) -> None: ...


class WagtailAdminDraftStateFormMixin:
    @property
    def show_schedule_publishing_toggle(self) -> bool: ...
    def clean(self): ...
