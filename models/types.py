from __future__ import annotations

from typing import TYPE_CHECKING, Any, Generic, Self, TypeAlias, cast

from django.db.models import (
    ForeignKey,
    JSONField,
    Manager,
    ManyToManyField as DjangoManyToManyField,
    Model,
    QuerySet,
)
from django.db.models.fields.related_descriptors import ReverseManyToOneDescriptor, ReverseOneToOneDescriptor
from modeltrans.manager import MultilingualManager, MultilingualQuerySet
from typing_extensions import TypeVar

from ..development.monkey import monkeypatch_generic_support

type NullableModel[M: Model] = M | None


_ST = TypeVar("_ST")
_GT = TypeVar("_GT", default=_ST)


FK: TypeAlias = ForeignKey[_ST, _GT]  # type: ignore  # noqa: UP040

_To = TypeVar("_To", bound=Model)
_Through = TypeVar("_Through", default=Any)

M2M: TypeAlias = DjangoManyToManyField[_To, _Through]  # noqa: UP040  # pyright: ignore


if not TYPE_CHECKING:
    monkeypatch_generic_support(JSONField)

_M = TypeVar("_M", bound=Model, covariant=True)  # noqa: PLC0105
_QS = TypeVar("_QS", bound=QuerySet[Model, Model], default=QuerySet[_M, _M])


class ModelQuerySet(QuerySet[_M, _M]):
    @classmethod
    def create_manager(cls) -> type[ModelManager[_M, Self]]:
        mgr = cast(type[ModelManager[_M, Self]], ModelManager.from_queryset(cls))
        setattr(mgr, '_built_with_as_manager', True)  # noqa: B010
        return mgr
    create_manager.queryset_only = True  # type: ignore

    #if TYPE_CHECKING:
    #    @classmethod
    #    def as_manager(cls) -> Manager[_M]: ...


class ModelManager(Generic[_M, _QS], Manager[_M]):
    if TYPE_CHECKING:
        def get_queryset(self) -> _QS: ...  # type: ignore[override]

    @classmethod
    def from_queryset(cls, queryset_class: type[_QS], class_name: str | None = None) -> type[ModelManager[_M, _QS]]:  # type: ignore[override]
        qs_module = queryset_class.__module__
        qs_name = queryset_class.__name__
        if class_name is None:
            if qs_name.endswith('QuerySet'):
                class_name = '%sManager' % qs_name.removesuffix('QuerySet')
            else:
                class_name = "%sFrom%s" % (cls.__name__, queryset_class.__name__)

        mgr_class = type(
            class_name,
            (cls,),
            {
                "_queryset_class": queryset_class,
                **cls._get_queryset_methods(queryset_class),
            },
        )
        mgr_class.__module__ = qs_module
        return mgr_class

    @property
    def qs(self) -> _QS:
        return self.get_queryset()


_MLQS = TypeVar("_MLQS", bound=MultilingualQuerySet, default=MultilingualQuerySet[_M])

class MLModelManager(MultilingualManager[_M], ModelManager[_M, _MLQS]):
    if TYPE_CHECKING:
        @classmethod
        def from_queryset(cls, queryset_class: type[_MLQS], class_name: str | None = None) -> type[MLModelManager[_M, _MLQS]]: ...  # type: ignore[override]
        def get_queryset(self) -> _MLQS: ...  # type: ignore[override]


def manager_from_qs[_M: Model, _QS: QuerySet](qs: type[_QS]) -> ModelManager[_M, _QS]:  # pyright: ignore
    return ModelManager[_M, _QS].from_queryset(qs)()

def manager_from_mlqs[_M: Model, _MLQS: MultilingualQuerySet](qs: type[_MLQS]) -> MLModelManager[_M, _MLQS]:
    return MLModelManager[_M, _MLQS].from_queryset(qs)()


type MLMM[_M: Model, _MLQS: MultilingualQuerySet] = MLModelManager[_M, _MLQS]

type RevMany[_To: Model] = ReverseManyToOneDescriptor[_To]
type RevOne[_From: Model, _To: Model] = ReverseOneToOneDescriptor[_From, _To]
