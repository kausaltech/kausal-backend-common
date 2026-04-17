from __future__ import annotations

from uuid import UUID

import pytest

from kausal_common.datasets.models import DimensionCategory
from kausal_common.datasets.tests.factories import DimensionCategoryFactory, DimensionFactory

pytestmark = pytest.mark.django_db


def _make_categories(labels: list[str]) -> list[DimensionCategory]:
    dimension = DimensionFactory.create()
    return [
        DimensionCategoryFactory.create(dimension=dimension, identifier=label.lower().replace(' ', '_'), label=label)
        for label in labels
    ]


def _ordered_labels(dimension_id: int) -> list[str]:
    return list(
        DimensionCategory.objects.filter(dimension_id=dimension_id).order_by('order', 'pk').values_list('label', flat=True)
    )


def _finalize(categories: list[DimensionCategory]) -> None:
    DimensionCategory.finalize_sibling_order(categories[0].dimension.categories.all(), hinted=categories)


def test_finalize_sibling_order_accepts_final_sibling_chain() -> None:
    climate, energy, infrastructure, operations = _make_categories([
        'Climate Change',
        'Energy Costs',
        'Infrastructure',
        'Operations',
    ])

    climate.next_sibling = infrastructure.uuid
    infrastructure.previous_sibling = climate.uuid
    infrastructure.next_sibling = energy.uuid
    energy.previous_sibling = infrastructure.uuid
    energy.next_sibling = operations.uuid
    operations.previous_sibling = energy.uuid

    _finalize([climate, infrastructure, energy, operations])

    assert _ordered_labels(climate.dimension_id) == [
        'Climate Change',
        'Infrastructure',
        'Energy Costs',
        'Operations',
    ]


def test_finalize_sibling_order_rejects_inconsistent_final_sibling_pair() -> None:
    a, b, c = _make_categories(['A', 'B', 'C'])

    b.previous_sibling = c.uuid
    b.next_sibling = a.uuid

    with pytest.raises(
        ValueError,
        match=(
            f'Item {b.uuid} has inconsistent sibling hints: it is not between previous_sibling {c.uuid} and next_sibling {a.uuid}'
        ),
    ):
        _finalize([b])


def test_finalize_sibling_order_rejects_unknown_sibling() -> None:
    a, b = _make_categories(['A', 'B'])

    b.previous_sibling = UUID('00000000-0000-0000-0000-000000000001')

    with pytest.raises(ValueError, match=f'Sibling {b.previous_sibling} not found'):
        _finalize([b])

    assert _ordered_labels(a.dimension_id) == ['A', 'B']
