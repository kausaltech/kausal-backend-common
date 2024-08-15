from __future__ import annotations

from typing import Iterable, Protocol


class HasPublicFields(Protocol):
    public_fields: list[str]


def public_fields(
    model: HasPublicFields,
    add_fields: Iterable[str] | None = None,
    remove_fields: Iterable[str] | None = None,
) -> list[str]:
    fields: list[str] = []
    if 'id' not in model.public_fields:
        fields.append('id')
    fields += list(model.public_fields)
    if remove_fields is not None:
        fields = [f for f in fields if f not in remove_fields]
    if add_fields is not None:
        fields += add_fields
    return fields
