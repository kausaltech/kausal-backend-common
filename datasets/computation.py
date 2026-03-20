from __future__ import annotations

import uuid as uuid_lib
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .models import DatasetMetric, DatasetMetricComputation, DimensionCategory

if TYPE_CHECKING:
    from collections.abc import Sequence
    from datetime import date
    from decimal import Decimal
    from typing import Any

    from django.db.models import QuerySet

    from .models import Dataset

# Sentinel metric ID used for NULL operand_a (indicator's own values)
_NULL_OPERAND_SENTINEL: int | None = None

# Namespace for generating deterministic UUIDs for virtual metrics
_VIRTUAL_METRIC_NAMESPACE = uuid_lib.UUID('a1b2c3d4-e5f6-7890-abcd-ef1234567890')


def get_indicator_virtual_metric_uuid(indicator_id: int) -> uuid_lib.UUID:
    """Return a deterministic UUID for an indicator's virtual metric in the dataset editor."""
    return uuid_lib.uuid5(_VIRTUAL_METRIC_NAMESPACE, f'indicator-values-{indicator_id}')


def get_indicator_virtual_datapoint_uuid(indicator_id: int, date_str: str, dim_cat_uuids: str) -> uuid_lib.UUID:
    """Return a deterministic UUID for a synthetic data point from indicator values."""
    return uuid_lib.uuid5(_VIRTUAL_METRIC_NAMESPACE, f'indicator-dp-{indicator_id}-{date_str}-{dim_cat_uuids}')


@dataclass
class ComputedValue:
    """A computed metric value with resolved ORM instances, ready for serialization."""

    date: date
    value: Decimal | None
    metric: DatasetMetric
    dimension_categories: list[DimensionCategory]


def _apply_op(op: str, a: Decimal | None, b: Decimal | None) -> Decimal | None:
    if a is None or b is None:
        return None
    match op:
        case 'multiply':
            return a * b
        case 'divide':
            return a / b if b != 0 else None
        case 'add':
            return a + b
        case 'subtract':
            return a - b
        case _:
            raise ValueError(f'Unknown operation: {op}')


def _compute_metric_values(
    values: dict[tuple[date, frozenset[int], int | None], Decimal | None],
    computations: Sequence[DatasetMetricComputation],
) -> list[tuple[date, frozenset[int], int, Decimal | None]]:
    """
    Apply computation definitions and return raw computed tuples.

    ``values`` is a lookup of (date, dimension_category_ids, metric_id) -> value,
    built by the caller from DataPoints, IndicatorGoalDataPoints, or any source.
    A metric_id of ``None`` represents the indicator's own values (NULL operand_a).

    Computations are applied in order, so earlier results can feed later ones.
    """
    results: list[tuple[date, frozenset[int], int, Decimal | None]] = []

    for comp in computations:
        a_id = comp.operand_a_id  # None for virtual indicator values
        b_id = comp.operand_b_id
        keys = {(d, dims) for d, dims, m in values if m in (a_id, b_id)}
        for d, dims in sorted(keys):
            key_a = (d, dims, a_id)
            key_b = (d, dims, b_id)
            if key_a not in values or key_b not in values:
                continue
            a = values[key_a]
            b = values[key_b]
            result = _apply_op(comp.operation, a, b)
            values[(d, dims, comp.target_metric_id)] = result
            results.append((d, dims, comp.target_metric_id, result))

    return results


def _build_values_lookup(
    data_points: QuerySet[Any],
) -> dict[tuple[date, frozenset[int], int | None], Decimal | None]:
    """Build a lookup dict from data points keyed by (date, dim_cat_ids, metric_id)."""
    values: dict[tuple[date, frozenset[int], int | None], Decimal | None] = {}
    for dp in data_points:
        dim_cat_ids = frozenset(dc.id for dc in dp.dimension_categories.all())
        values[(dp.date, dim_cat_ids, dp.metric_id)] = dp.value
    return values


def _inject_null_operand_values(
    values: dict[tuple[date, frozenset[int], int | None], Decimal | None],
    dataset: Dataset,
    computations: Sequence[DatasetMetricComputation],
) -> None:
    """
    If any computation has operand_a=NULL, resolve indicator values and inject them.

    Indicator values are keyed with metric_id=None (the sentinel for NULL operand_a).
    """
    has_null_operand = any(comp.operand_a_id is None for comp in computations)
    if not has_null_operand:
        return

    from .config import dataset_config
    null_values = dataset_config.resolve_null_operand_values(dataset)
    for (d, dims), val in null_values.items():
        values[(d, dims, _NULL_OPERAND_SENTINEL)] = val


def _resolve_computed_values(
    raw: list[tuple[date, frozenset[int], int, Decimal | None]],
) -> list[ComputedValue]:
    """Bulk-fetch ORM instances and build ComputedValue objects from raw tuples."""
    if not raw:
        return []

    metric_ids = {r[2] for r in raw}
    all_dim_cat_ids: set[int] = set()
    for _, dims, _, _ in raw:
        all_dim_cat_ids |= dims

    metrics_by_id = {m.id: m for m in DatasetMetric.objects.filter(id__in=metric_ids)}
    dim_cats_by_id = {dc.id: dc for dc in DimensionCategory.objects.filter(id__in=all_dim_cat_ids)} if all_dim_cat_ids else {}

    return [
        ComputedValue(
            date=d,
            value=val,
            metric=metrics_by_id[metric_id],
            dimension_categories=[dim_cats_by_id[dc_id] for dc_id in sorted(dims)],
        )
        for d, dims, metric_id, val in raw
    ]


def compute_for_queryset(
    dataset: Dataset,
    data_points: QuerySet[Any],
) -> list[ComputedValue]:
    """Compute metric values from a data point queryset."""
    computations = list(
        DatasetMetricComputation.objects.filter(schema=dataset.schema).select_related(
            'target_metric',
            'operand_a',
            'operand_b',
        )
    )
    if not computations:
        return []

    values = _build_values_lookup(data_points.prefetch_related('dimension_categories'))
    _inject_null_operand_values(values, dataset, computations)
    raw = _compute_metric_values(values, computations)
    return _resolve_computed_values(raw)


def compute_dataset_values(dataset: Dataset) -> list[ComputedValue]:
    """
    Compute metric values for a dataset's actual data points.

    Fetches data points, applies computations, and returns resolved
    ComputedValue instances.
    """
    return compute_for_queryset(dataset, dataset.data_points.all())  # type: ignore[attr-defined]
