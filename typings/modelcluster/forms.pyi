from typing import Any, Callable, Generic, Mapping, type_check_only
from typing_extensions import TypeVar

from django.db.models import Model
from django.forms import inlineformset_factory
from django.forms.formsets import TOTAL_FORM_COUNT as TOTAL_FORM_COUNT
from django.forms.models import (
    BaseModelFormSet,
    ModelForm,
    ModelFormMetaclass,
    ModelFormOptions,
    modelform_factory,
    modelformset_factory,
)
from modelcluster.models import get_all_child_relations as get_all_child_relations

_M = TypeVar("_M", bound=Model, default=Model)
_ModelFormT = TypeVar("_ModelFormT", bound=ModelForm, default=ModelForm)


class BaseTransientModelFormSet(BaseModelFormSet[_M, _ModelFormT]):
    """ A ModelFormSet that doesn't assume that all its initial data instances exist in the db """
    changed_objects: list[tuple[_M, list[str]]]
    deleted_objects: list[_M]
    def save_existing_objects(self, commit: bool = True): ...


_F = TypeVar('_F', bound=Callable[..., Any])

@type_check_only
class copy_signature(Generic[_F]):  # noqa: N801
    def __init__(self, target: _F) -> None: ...
    def __call__(self, wrapped: Callable[..., Any]) -> _F: ...

@copy_signature(modelformset_factory)
def transientmodelformset_factory(*args, **kwargs): ...


class BaseChildFormSet(BaseTransientModelFormSet[_M, _ModelFormT]):
    inherit_kwargs: dict[str, Any]
    instance: _M
    rel_name: str

    def save(self, commit: bool = True) -> list[_M]: ...
    def clean(self, *args, **kwargs): ...
    def validate_unique(self) -> None:
        """This clean method will check for unique_together condition"""


@copy_signature(inlineformset_factory)
def childformset_factory(*args, **kwargs): ...


class ClusterFormOptions(ModelFormOptions[_M]):
    formsets: dict[str, Any]  # TODO
    exclude_formsets: list[str]
    def __init__(self, options: type | None = None) -> None: ...


class ClusterFormMetaclass(ModelFormMetaclass):
    extra_form_count: int
    @classmethod
    def child_form(cls) -> type[ClusterForm]: ...


class ClusterForm(ModelForm[_M], metaclass=ClusterFormMetaclass):
    formsets: Mapping[str, BaseModelFormSet[Any, Any]]


@copy_signature(modelform_factory)
def clusterform_factory(*args, **kwargs): ...
