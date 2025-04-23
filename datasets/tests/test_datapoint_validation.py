from __future__ import annotations

import datetime
from decimal import Decimal

import pytest
from pytest_factoryboy import register
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIRequestFactory

from kausal_common.datasets.api import DataPointSerializer
from kausal_common.datasets.models import DataPoint

from .factories import (
    DataPointFactory,
    DatasetFactory,
    DatasetMetricFactory,
    DatasetSchemaFactory,
    DimensionCategoryFactory,
    DimensionFactory,
)

pytestmark = pytest.mark.django_db

# Register factories
register(DatasetSchemaFactory)
register(DimensionFactory)
register(DimensionCategoryFactory)
register(DatasetMetricFactory)
register(DatasetFactory)
register(DataPointFactory)


@pytest.fixture
def api_factory():
    return APIRequestFactory()


@pytest.fixture
def schema(dataset_schema_factory):
    return dataset_schema_factory()


@pytest.fixture
def dimension(dimension_factory, schema):
    dimension = dimension_factory()
    schema.dimensions.create(dimension=dimension)
    return dimension


@pytest.fixture
def dimension_categories(dimension_category_factory, dimension):
    category1 = dimension_category_factory(dimension=dimension, label='Category 1')
    category2 = dimension_category_factory(dimension=dimension, label='Category 2')
    return category1, category2


@pytest.fixture
def metric(dataset_metric_factory, schema):
    return dataset_metric_factory(schema=schema)


@pytest.fixture
def dataset(dataset_factory, schema):
    return dataset_factory(schema=schema)


@pytest.fixture
def existing_datapoint(data_point_factory, dataset, metric, dimension_categories):
    category1, _ = dimension_categories
    return data_point_factory(
        dataset=dataset,
        date=datetime.date(2023, 1, 1),
        metric=metric,
        value=Decimal('100'),
        dimension_categories=[category1]
    )


@pytest.fixture
def serializer_context(dataset, api_factory):
    request = api_factory.post(f'/datasets/{dataset.uuid}/datapoints/')
    return {
        'view': type('obj', (object,), {
            'kwargs': {'dataset_uuid': str(dataset.uuid)}
        }),
        'request': request
    }


def test_duplicate_datapoint_validation(existing_datapoint, metric, dimension_categories, serializer_context):
    """Test that trying to create a duplicate datapoint raises validation error."""
    category1, _ = dimension_categories

    data = {
        'date': '2023-01-01',
        'dimension_categories': [str(category1.uuid)],
        'metric': str(metric.uuid),
        'value': '200'
    }

    # Test that validation raises an error
    serializer = DataPointSerializer(data=data, context=serializer_context)
    with pytest.raises(ValidationError) as exc_info:
        serializer.is_valid(raise_exception=True)

    # Check error message
    assert 'A data point with this date and dimension category combination already exists' in str(exc_info.value)


def test_different_dimension_categories_passes(existing_datapoint, metric, dimension_categories, serializer_context):
    """Test that creating datapoints with different dimension categories passes."""
    _, category2 = dimension_categories

    data = {
        'date': '2023-01-01',
        'dimension_categories': [str(category2.uuid)],
        'metric': str(metric.uuid),
        'value': '200'
    }

    # Test that validation passes
    serializer = DataPointSerializer(data=data, context=serializer_context)
    assert serializer.is_valid()


def test_different_date_passes(existing_datapoint, metric, dimension_categories, serializer_context):
    """Test that creating datapoints with different dates passes."""
    category1, _ = dimension_categories

    data = {
        'date': '2024-01-01',
        'dimension_categories': [str(category1.uuid)],
        'metric': str(metric.uuid),
        'value': '200'
    }

    # Test that validation passes
    serializer = DataPointSerializer(data=data, context=serializer_context)
    assert serializer.is_valid()
