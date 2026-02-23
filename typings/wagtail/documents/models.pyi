from collections.abc import Generator, Sequence
from typing import Any, ClassVar

from django.contrib.auth.models import AbstractUser
from django.core.files.base import File
from django.db import models
from django.db.models.expressions import Combinable
from django.db.models.options import Options
from django.dispatch import Signal
from wagtail.models import CollectionMember
from wagtail.models.reference_index import ReferenceGroups
from wagtail.search.queryset import SearchableQuerySetMixin

from modelsearch import index

class DocumentQuerySet[M: AbstractDocument = Document](SearchableQuerySetMixin, models.QuerySet[M]): ...

class AbstractDocument(CollectionMember, index.Indexed, models.Model):
    title: models.CharField[str | int | Combinable, str]
    file: models.FileField
    created_at: models.DateTimeField[str | models.DateTimeField | models.DateField | Combinable, models.DateTimeField]
    uploaded_by_user: models.ForeignKey[Any | None, Any | None]
    file_size: models.PositiveIntegerField[float | int | str | Combinable, int]
    file_hash: models.CharField[str | int | Combinable, str]

    search_fields: Sequence[index.BaseField]

    class Meta(Options): ...

    def is_stored_locally(self) -> bool: ...
    def open_file(self) -> Generator[File]: ...
    def get_file_size(self) -> int | None: ...
    def get_file_hash(self) -> str: ...
    @property
    def filename(self) -> str: ...
    @property
    def file_extension(self) -> str: ...
    @property
    def url(self) -> str: ...
    def get_usage(self) -> ReferenceGroups: ...
    @property
    def usage_url(self) -> str: ...
    def is_editable_by_user(self, user: AbstractUser) -> bool: ...
    @property
    def content_type(self) -> str: ...
    @property
    def content_disposition(self) -> str: ...


class Document(AbstractDocument):
    admin_form_fields: ClassVar[tuple[str, ...]]
    class Meta(AbstractDocument.Meta): ...


document_served: Signal
