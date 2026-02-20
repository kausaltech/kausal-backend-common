from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

    from django.db.models import Model


def ignore_wagtail_reference_index[M: 'Model'](field_names: list[str]) -> Callable[[type[M]], type[M]]:
    """
    Class decorator that sets wagtail_reference_index_ignore = True on the given model fields.

    Use for ForeignKeys and other fields that should be excluded from Wagtail's reference index.
    """
    def decorator(cls: type[M]) -> type[M]:
        for name in field_names:
            field = cls._meta.get_field(name)
            setattr(field, "wagtail_reference_index_ignore", True)  # noqa: B010
        return cls
    return decorator
