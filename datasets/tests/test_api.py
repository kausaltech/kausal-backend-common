from decimal import Decimal

from rest_framework.test import APIRequestFactory

import pytest
from pytest_factoryboy import register

from kausal_common.datasets.api import DataPointSerializer
from kausal_common.datasets.tests.factories import (
    DataPointFactory,
    DatasetFactory,
    DatasetMetricFactory,
    DatasetSchemaDimensionFactory,
    DatasetSchemaFactory,
    DimensionCategoryFactory,
    DimensionFactory,
)

pytestmark = pytest.mark.django_db


# Registering factories copied from test_datapoint_validation.py
register(DatasetSchemaDimensionFactory)
register(DatasetSchemaFactory)
register(DimensionFactory)
register(DimensionCategoryFactory)
register(DatasetMetricFactory)
register(DatasetFactory)


# Fixtures copied from test_datapoint_validation.py
@pytest.fixture
def api_factory():
    return APIRequestFactory()


@pytest.fixture
def dimension_categories(dimension_category_factory, dimension):
    category1 = dimension_category_factory(dimension=dimension, label='Category 1')
    category2 = dimension_category_factory(dimension=dimension, label='Category 2')
    return category1, category2


@pytest.fixture
def serializer_context(dataset, api_factory):
    request = api_factory.post(f'/datasets/{dataset.uuid}/data_points/')
    return {
        'view': type('obj', (object,), {
            'kwargs': {'dataset_uuid': str(dataset.uuid)}
        }),
        'request': request
    }


def test_data_point_bulk_serializer_save_without_changes_keeps_data(serializer_context):
    ds = DatasetFactory.create()
    data_points = [DataPointFactory.create(dataset=ds) for _ in range(2)]
    serialized_data_points = [
        DataPointSerializer(instance=data_point, context=serializer_context).data
        for data_point in data_points
    ]
    bulk_serializer = DataPointSerializer(
        many=True, data=serialized_data_points, instance=ds.data_points.all(), context=serializer_context
    )
    assert bulk_serializer.is_valid()
    bulk_serializer.save()
    serialized_data_points_after_save = [
        DataPointSerializer(instance=data_point, context=serializer_context).data
        for data_point in ds.data_points.all()
    ]
    assert serialized_data_points_after_save == serialized_data_points


def test_data_point_bulk_serializer_save_with_changes_updates_data(serializer_context):
    ds = DatasetFactory.create()
    data_points = [DataPointFactory.create(dataset=ds) for _ in range(2)]
    serialized_data_points = [
        DataPointSerializer(instance=data_point, context=serializer_context).data
        for data_point in data_points
    ]
    # Change the `value` field of each data point
    changed_serialized_data_points = [
        {**data, 'value': data['value'] + 1}
        for data in serialized_data_points
    ]
    bulk_serializer = DataPointSerializer(
        many=True, data=changed_serialized_data_points, instance=ds.data_points.all(), context=serializer_context
    )
    assert bulk_serializer.is_valid()
    bulk_serializer.save()
    serialized_data_points_after_save = [
        DataPointSerializer(instance=data_point, context=serializer_context).data
        for data_point in ds.data_points.all()
    ]
    assert serialized_data_points_after_save == changed_serialized_data_points


def test_data_point_bulk_serializer_create(
    dataset, dataset_metric, dimension_categories, serializer_context, dataset_schema_dimension
):
    category1, category2 = dimension_categories
    initial_data = [
        {
            # If we pass `dataset` here, it will be ignored (i.e., not put into `DataPointSerializer.data`) as it's a
            # read-only field. We need to pass it to `DataPointSerializer.save()`, as we do in
            # `DataPointViewSet.perform_create()`.
            'date': '2023-01-01',
            'dimension_categories': [str(category1.uuid)],
            'metric': str(dataset_metric.uuid),
            'value': Decimal('1.0'),
        },
        {
            'date': '2024-01-01',
            'dimension_categories': [str(category2.uuid)],
            'metric': str(dataset_metric.uuid),
            'value': Decimal('2.0'),
        }
    ]
    bulk_serializer = DataPointSerializer(many=True, data=initial_data, context=serializer_context)
    assert bulk_serializer.is_valid()
    bulk_serializer.save(dataset=dataset)
    serialized_data_points_after_save = [
        DataPointSerializer(instance=data_point, context=serializer_context).data
        for data_point in dataset.data_points.all()
    ]
    # `serialized_data_points_after_save` should differ from `initial_data` only by new UUID values and the dataset that
    # we passed to `bulk_serializer.save()`.
    data_to_compare = [
        {k: v for k, v in serialized_data_point.items() if k not in ('uuid', 'dataset')}
        for serialized_data_point in serialized_data_points_after_save
    ]
    assert data_to_compare == initial_data
