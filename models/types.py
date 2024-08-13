from __future__ import annotations

from typing import TYPE_CHECKING, Any, Generic, TypeAlias, overload

from django.db.models import (
    ForeignKey,
    JSONField,
    Manager,
    ManyToManyField,
    Model,
    OneToOneField,
    QuerySet,
)
from modeltrans.manager import MultilingualManager, MultilingualQuerySet

from typing_extensions import TypeVar

from ..development.monkey import monkeypatch_generic_support

type NullableModel[M: Model] = M | None


_To = TypeVar("_To", bound=Model)
_Through = TypeVar("_Through", default=Any)

#
# Type annotation helpers for foreign relationships
#
if TYPE_CHECKING:
    # These should only be used in typing scope.
    from django.db.models.fields.related_descriptors import RelatedManager, ReverseManyToOneDescriptor, ReverseOneToOneDescriptor

    type FK[To: Model | None] = ForeignKey[To, To]

    class RelatedManagerQS[To: Model, QS: QuerySet](RelatedManager[To]):  # pyright: ignore
        def get_queryset(self) -> QS: ...


    class ReverseManyToOneDescriptorQS[To: Model, QS: QuerySet](ReverseManyToOneDescriptor[To]):
        @overload    # type: ignore
        def __get__(self, instance: Model, cls: Any = ...) -> RelatedManagerQS[_To, QS]: ...  # noqa: ANN401  # type: ignore

    type RevMany[To: Model] = ReverseManyToOneDescriptor[To]
    type RevManyQS[To: Model, QS: QuerySet] = ReverseManyToOneDescriptorQS[To, QS]

    type OneToOne[To: Model | None] = OneToOneField[To, To]
    type RevOne[From: Model, To: Model] = ReverseOneToOneDescriptor[From, To]

    M2M: TypeAlias = ManyToManyField[_To, _Through]  # noqa: UP040  # pyright: ignore


if not TYPE_CHECKING:
    monkeypatch_generic_support(JSONField)

_M = TypeVar("_M", bound=Model, covariant=True)  # noqa: PLC0105
_QS = TypeVar("_QS", bound=QuerySet[Model, Model], default=QuerySet[_M, _M])


class ModelManager(Generic[_M, _QS], Manager[_M]):
    """
    Subclassed Manager that enables easier type checking with custom querysets.

    Example:
    -------
    class MyModelQuerySet(models.QuerySet['MyModel']):
        def my_custom_method(self):
            return self.filter(abc='def')

    if TYPE_CHECKING:
        class MyModelManager(ModelManager['MyModel', MyModelQuerySet]): ...
    else:
        MyModelManager = ModelManager.from_queryset(MyModelQuerySet)


    class MyModel(models.Model):
        pass

    """

    if TYPE_CHECKING:
        def get_queryset(self) -> _QS: ...  # type: ignore[override]
        """Returns a correctly typed QuerySet"""

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
    """
    ModelManager that supports modeltrans querysets.

    Note that you need to also use an instance of MultilingualQuerySet.
    """

    if TYPE_CHECKING:
        @classmethod
        def from_queryset(cls, queryset_class: type[_MLQS], class_name: str | None = None) -> type[MLModelManager[_M, _MLQS]]: ...  # type: ignore[override]
        def get_queryset(self) -> _MLQS: ...  # type: ignore[override]


def manager_from_qs[_M: Model, _QS: QuerySet](qs: type[_QS]) -> ModelManager[_M, _QS]:  # pyright: ignore
    return ModelManager[_M, _QS].from_queryset(qs)()

def manager_from_mlqs[_M: Model, _MLQS: MultilingualQuerySet](qs: type[_MLQS]) -> MLModelManager[_M, _MLQS]:
    return MLModelManager[_M, _MLQS].from_queryset(qs)()


if TYPE_CHECKING:
    type MLMM[_M: Model, _MLQS: MultilingualQuerySet] = MLModelManager[_M, _MLQS]
