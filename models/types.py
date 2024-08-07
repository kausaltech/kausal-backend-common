from typing import TYPE_CHECKING

from django.db.models import (
    ForeignKey as DjangoForeignKey,
    JSONField,  # noqa: F401
    ManyToManyField as DjangoManyToManyField,
    Model,
)

from ..typings.monkey import monkeypatch_generic_support

type NullableModel[M: Model] = M | None

type ForeignKey[M: Model] = DjangoForeignKey[M, M]  # pyright: ignore
type NullableFK[M: Model] = DjangoForeignKey[M | None, M | None]  # pyright: ignore
type ManyToManyField[To: Model, Through: Model] = DjangoManyToManyField[To, Through]


if TYPE_CHECKING:
    from django.db.models.fields.related_descriptors import RelatedManager  # pyright: ignore
    from django.db.models.manager import RelatedManager  # type: ignore  # noqa: F811
else:
    monkeypatch_generic_support(JSONField)
