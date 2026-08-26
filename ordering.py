from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from uuid import UUID


class UUIDIdentified(Protocol):
    """Structural type for objects with stable UUID identity."""

    @property
    def uuid(self) -> UUID: ...


class SiblingOrderHint(UUIDIdentified, Protocol):
    """Structural type for an object's sibling-relative position."""

    @property
    def previous_sibling(self) -> UUID | None: ...

    @property
    def next_sibling(self) -> UUID | None: ...


class InconsistentSiblingOrderError(ValueError):
    """Raised when previous and next sibling hints do not describe one gap."""


def reorder_siblings[T: UUIDIdentified](
    siblings: Sequence[T],
    hinted: Sequence[SiblingOrderHint] = (),
) -> list[T]:
    """Return siblings reordered according to UUID-based relative-position hints."""
    by_uuid = {sibling.uuid: sibling for sibling in siblings}
    if len(by_uuid) != len(siblings):
        raise ValueError('Sibling UUIDs must be unique')

    order_list = list(by_uuid)
    for item in hinted:
        item_uuid = item.uuid
        if item_uuid not in by_uuid:
            raise ValueError(f'Item {item_uuid} not found among siblings')

        prev_uuid = item.previous_sibling
        next_uuid = item.next_sibling
        if prev_uuid is None and next_uuid is None:
            continue
        if item_uuid in (prev_uuid, next_uuid):
            raise ValueError(f'Item {item_uuid} cannot be its own sibling')

        order_list.remove(item_uuid)

        prev_idx: int | None = None
        next_idx: int | None = None
        if prev_uuid is not None:
            _check_sibling_exists(prev_uuid, by_uuid)
            prev_idx = _find_sibling_index(prev_uuid, order_list)
        if next_uuid is not None:
            _check_sibling_exists(next_uuid, by_uuid)
            next_idx = _find_sibling_index(next_uuid, order_list)

        insert_idx = prev_idx + 1 if prev_idx is not None else next_idx
        assert insert_idx is not None
        order_list.insert(insert_idx, item_uuid)

    _check_consistent_sibling_pairs(order_list, hinted)
    return [by_uuid[uuid] for uuid in order_list]


def _check_sibling_exists(ref_uuid: UUID, by_uuid: Mapping[UUID, UUIDIdentified]) -> None:
    if ref_uuid not in by_uuid:
        raise ValueError(f'Sibling {ref_uuid} not found')


def _find_sibling_index(ref_uuid: UUID, order_list: list[UUID]) -> int:
    try:
        return order_list.index(ref_uuid)
    except ValueError:
        raise ValueError(f'Sibling {ref_uuid} not found in current ordering') from None


def _check_consistent_sibling_pairs(order_list: list[UUID], hinted: Sequence[SiblingOrderHint]) -> None:
    order_idx = {uuid: idx for idx, uuid in enumerate(order_list)}
    for item in hinted:
        prev_uuid = item.previous_sibling
        next_uuid = item.next_sibling
        if prev_uuid is None or next_uuid is None:
            continue

        item_uuid = item.uuid
        item_idx = order_idx[item_uuid]
        if order_idx[prev_uuid] + 1 != item_idx or item_idx + 1 != order_idx[next_uuid]:
            raise InconsistentSiblingOrderError(
                f'Item {item_uuid} has inconsistent sibling hints: it is not between '
                + f'previous_sibling {prev_uuid} and next_sibling {next_uuid}'
            )
