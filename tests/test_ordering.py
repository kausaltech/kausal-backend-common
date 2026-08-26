from dataclasses import dataclass
from uuid import UUID

import pytest

from kausal_common.ordering import reorder_siblings


@dataclass(frozen=True)
class Item:
    uuid: UUID


@dataclass(frozen=True)
class Hint:
    uuid: UUID
    previous_sibling: UUID | None = None
    next_sibling: UUID | None = None


def _item(value: int) -> Item:
    return Item(UUID(int=value))


def test_reorder_siblings_accepts_structural_uuid_objects() -> None:
    first, second, third = (_item(value) for value in range(1, 4))

    reordered = reorder_siblings(
        [first, second, third],
        hinted=[Hint(third.uuid, previous_sibling=first.uuid, next_sibling=second.uuid)],
    )

    assert reordered == [first, third, second]


def test_reorder_siblings_rejects_inconsistent_pair() -> None:
    first, second, third, fourth = (_item(value) for value in range(1, 5))

    with pytest.raises(ValueError, match='inconsistent sibling hints'):
        reorder_siblings(
            [first, second, third, fourth],
            hinted=[Hint(fourth.uuid, previous_sibling=first.uuid, next_sibling=third.uuid)],
        )


def test_reorder_siblings_rejects_self_reference() -> None:
    item = _item(1)

    with pytest.raises(ValueError, match='cannot be its own sibling'):
        reorder_siblings([item], hinted=[Hint(item.uuid, previous_sibling=item.uuid)])
