from __future__ import annotations

import datetime
from decimal import Decimal

from rest_framework.exceptions import ValidationError
from rest_framework.test import APIRequestFactory

import pytest

from kausal_common.datasets.api import DataPointSerializer
from kausal_common.datasets.models import DatasetSchema

from .factories import (
    DataPointFactory,
    DatasetFactory,
    DatasetMetricFactory,
    DatasetSchemaFactory,
    DimensionCategoryFactory,
    DimensionFactory,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_factory():
    return APIRequestFactory()


@pytest.fixture
def schema():
    return DatasetSchemaFactory.create()


@pytest.fixture
def dimension(schema):
    dimension = DimensionFactory.create()
    schema.dimensions.create(dimension=dimension)
    return dimension


@pytest.fixture
def dimension_categories(dimension):
    category1 = DimensionCategoryFactory.create(dimension=dimension, label='Category 1')
    category2 = DimensionCategoryFactory.create(dimension=dimension, label='Category 2')
    return category1, category2


@pytest.fixture
def metric(schema):
    return DatasetMetricFactory.create(schema=schema)


@pytest.fixture
def dataset(schema):
    return DatasetFactory.create(schema=schema)


@pytest.fixture
def existing_data_point(dataset, metric, dimension_categories):
    category1, _ = dimension_categories
    return DataPointFactory.create(
        dataset=dataset,
        date=datetime.date(2023, 1, 1),
        metric=metric,
        value=Decimal(100),
        dimension_categories=[category1]
    )


@pytest.fixture
def serializer_context(dataset, api_factory):
    request = api_factory.post(f'/datasets/{dataset.uuid}/data_points/')
    return {
        'view': type('obj', (object,), {
            'kwargs': {'dataset_uuid': str(dataset.uuid)}
        }),
        'request': request
    }


def test_duplicate_data_point_validation(existing_data_point, metric, dimension_categories, serializer_context):
    """Test that trying to create a duplicate data_point raises validation error."""
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
    assert 'A data point with this date, dimension category, and metric combination already exists.' in str(exc_info.value)


def test_different_dimension_categories_passes(existing_data_point, metric, dimension_categories, serializer_context):
    """Test that creating data points with different dimension categories passes."""
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


def test_different_date_passes(existing_data_point, metric, dimension_categories, serializer_context):
    """Test that creating data points with different dates passes."""
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


def test_different_metric_passes(existing_data_point, dimension_categories, serializer_context, schema):
    """Test that creating data points with different metrics passes."""
    category1, _ = dimension_categories

    # Create a different metric for the same schema
    different_metric = DatasetMetricFactory.create(schema=schema)

    data = {
        'date': '2023-01-01',
        'dimension_categories': [str(category1.uuid)],
        'metric': str(different_metric.uuid),
        'value': '200'
    }

    # Test that validation passes
    serializer = DataPointSerializer(data=data, context=serializer_context)
    assert serializer.is_valid()


# --- Monthly resolution tests ---

@pytest.fixture
def monthly_schema():
    schema = DatasetSchemaFactory.create()
    schema.time_resolution = DatasetSchema.TimeResolution.MONTHLY
    schema.save()
    return schema


@pytest.fixture
def monthly_dimension(monthly_schema):
    dimension = DimensionFactory.create()
    monthly_schema.dimensions.create(dimension=dimension)
    return dimension


@pytest.fixture
def monthly_dimension_categories(monthly_dimension):
    category1 = DimensionCategoryFactory.create(dimension=monthly_dimension, label='Category 1')
    category2 = DimensionCategoryFactory.create(dimension=monthly_dimension, label='Category 2')
    return category1, category2


@pytest.fixture
def monthly_metric(monthly_schema):
    return DatasetMetricFactory.create(schema=monthly_schema)


@pytest.fixture
def monthly_dataset(monthly_schema):
    return DatasetFactory.create(schema=monthly_schema)


@pytest.fixture
def monthly_existing_data_point(monthly_dataset, monthly_metric, monthly_dimension_categories):
    category1, _ = monthly_dimension_categories
    return DataPointFactory.create(
        dataset=monthly_dataset,
        date=datetime.date(2023, 3, 1),
        metric=monthly_metric,
        value=Decimal(100),
        dimension_categories=[category1],
    )


@pytest.fixture
def monthly_serializer_context(monthly_dataset, api_factory):
    request = api_factory.post(f'/datasets/{monthly_dataset.uuid}/data_points/')
    return {
        'view': type('obj', (object,), {
            'kwargs': {'dataset_uuid': str(monthly_dataset.uuid)}
        }),
        'request': request,
    }


def test_monthly_duplicate_same_year_and_month_raises(
    monthly_existing_data_point, monthly_metric, monthly_dimension_categories, monthly_serializer_context
):
    """Monthly resolution: same year+month+categories+metric should fail."""
    category1, _ = monthly_dimension_categories

    data = {
        'date': '2023-03-15',  # same year and month as existing point
        'dimension_categories': [str(category1.uuid)],
        'metric': str(monthly_metric.uuid),
        'value': '200',
    }

    serializer = DataPointSerializer(data=data, context=monthly_serializer_context)
    with pytest.raises(ValidationError) as exc_info:
        serializer.is_valid(raise_exception=True)

    assert 'A data point with this date, dimension category, and metric combination already exists.' in str(exc_info.value)


def test_monthly_different_month_passes(
    monthly_existing_data_point, monthly_metric, monthly_dimension_categories, monthly_serializer_context
):
    """Monthly resolution: same year but different month should pass."""
    category1, _ = monthly_dimension_categories

    data = {
        'date': '2023-04-01',  # different month from existing point (March)
        'dimension_categories': [str(category1.uuid)],
        'metric': str(monthly_metric.uuid),
        'value': '200',
    }

    serializer = DataPointSerializer(data=data, context=monthly_serializer_context)
    assert serializer.is_valid()


def test_yearly_same_year_different_month_raises(
    existing_data_point, metric, dimension_categories, serializer_context
):
    """Yearly resolution: same year but different month should still raise a validation error."""
    category1, _ = dimension_categories

    data = {
        'date': '2023-06-01',  # same year as existing (2023-01-01) but different month
        'dimension_categories': [str(category1.uuid)],
        'metric': str(metric.uuid),
        'value': '200',
    }

    serializer = DataPointSerializer(data=data, context=serializer_context)
    with pytest.raises(ValidationError) as exc_info:
        serializer.is_valid(raise_exception=True)

    assert 'A data point with this date, dimension category, and metric combination already exists.' in str(exc_info.value)
