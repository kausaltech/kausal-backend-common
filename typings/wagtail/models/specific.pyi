from collections.abc import Sequence
from typing import Generic, TypeVar

from django.contrib.contenttypes.models import ContentType
from django.db.models import Model
from django.utils.functional import cached_property as cached_property

_SpecificM_co = TypeVar('_SpecificM_co', bound=Model, covariant=True)


class SpecificMixin(Generic[_SpecificM_co]):
    """
    Mixin for models that support multi-table inheritance and provide a
    ``content_type`` field pointing to the specific model class, to provide
    methods and properties for retrieving the specific instance of the model.
    """
    def get_specific(
        self, deferred: bool = False, copy_attrs: Sequence[str] | None = None,
        copy_attrs_exclude: Sequence[str] | None = None,
    ) -> _SpecificM_co:
        """
        Return this object in its most specific subclassed form.

        By default, a database query is made to fetch all field values for the
        specific object. If you only require access to custom methods or other
        non-field attributes on the specific object, you can use
        ``deferred=True`` to avoid this query. However, any attempts to access
        specific field values from the returned object will trigger additional
        database queries.

        By default, references to all non-field attribute values are copied
        from current object to the returned one. This includes:

        * Values set by a queryset, for example: annotations, or values set as
          a result of using ``select_related()`` or ``prefetch_related()``.
        * Any ``cached_property`` values that have been evaluated.
        * Attributes set elsewhere in Python code.

        For fine-grained control over which non-field values are copied to the
        returned object, you can use ``copy_attrs`` to specify a complete list
        of attribute names to include. Alternatively, you can use
        ``copy_attrs_exclude`` to specify a list of attribute names to exclude.

        If called on an object that is already an instance of the most specific
        class, the object will be returned as is, and no database queries or
        other operations will be triggered.

        If the object was originally created using a model that has since
        been removed from the codebase, an instance of the base class will be
        returned (without any custom field values or other functionality
        present on the original class). Usually, deleting these objects is the
        best course of action, but there is currently no safe way for Wagtail
        to do that at migration time.
        """
    @cached_property
    def specific(self) -> _SpecificM_co:
        """
        Returns this object in its most specific subclassed form with all field
        values fetched from the database. The result is cached in memory.
        """
    @cached_property
    def specific_deferred(self):
        """
        Returns this object in its most specific subclassed form without any
        additional field values being fetched from the database. The result
        is cached in memory.
        """
    @cached_property
    def specific_class(self) -> type[_SpecificM_co]:
        """
        Return the class that this object would be if instantiated in its
        most specific form.

        If the model class can no longer be found in the codebase, and the
        relevant ``ContentType`` has been removed by a database migration,
        the return value will be ``None``.

        If the model class can no longer be found in the codebase, but the
        relevant ``ContentType`` is still present in the database (usually a
        result of switching between git branches without running or reverting
        database migrations beforehand), the return value will be ``None``.
        """
    @property
    def cached_content_type(self) -> ContentType:
        """
        Return this object's ``content_type`` value from the ``ContentType``
        model's cached manager, which will avoid a database query if the
        content type is already in memory.
        """
