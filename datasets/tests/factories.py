from __future__ import annotations

import datetime
from decimal import Decimal

from factory import Sequence, SubFactory, post_generation
from factory.django import DjangoModelFactory

from kausal_common.datasets.models import (
    DataPoint,
    Dataset,
    DatasetMetric,
    DatasetSchema,
    DatasetSchemaDimension,
    Dimension,
    DimensionCategory,
)


class DatasetSchemaFactory(DjangoModelFactory[DatasetSchema]):
    class Meta:
        model = DatasetSchema

    name = Sequence(lambda n: f'Test Schema {n}')


class DimensionFactory(DjangoModelFactory[Dimension]):
    class Meta:
        model = Dimension

    name = Sequence(lambda n: f'Test Dimension {n}')


class DimensionCategoryFactory(DjangoModelFactory[DimensionCategory]):
    class Meta:
        model = DimensionCategory

    dimension = SubFactory[DimensionCategory, Dimension](DimensionFactory)
    label = Sequence(lambda n: f'Category {n}')


class DatasetMetricFactory(DjangoModelFactory[DatasetMetric]):
    class Meta:
        model = DatasetMetric

    schema = SubFactory[DatasetMetric, DatasetSchema](DatasetSchemaFactory)
    label = Sequence(lambda n: f'Test Metric {n}')


class DatasetSchemaDimensionFactory(DjangoModelFactory[DatasetSchemaDimension]):
    class Meta:
        model = DatasetSchemaDimension

    schema = SubFactory[DatasetSchemaDimension, DatasetSchema](DatasetSchemaFactory)
    dimension = SubFactory[DatasetSchemaDimension, Dimension](DimensionFactory)


class DatasetFactory(DjangoModelFactory[Dataset]):
    class Meta:
        model = Dataset

    schema = SubFactory[Dataset, DatasetSchema](DatasetSchemaFactory)


class DataPointFactory(DjangoModelFactory[DataPoint]):
    class Meta:
        model = DataPoint
        skip_postgeneration_save = True

    dataset = SubFactory[DataPoint, Dataset](DatasetFactory)
    metric = SubFactory[DataPoint, DatasetMetric](DatasetMetricFactory)
    date = datetime.date(2023, 1, 1)
    value = Decimal(100)

    @post_generation
    @staticmethod
    def dimension_categories(obj: DataPoint, create: bool, extracted: list[DimensionCategory]) -> None:
        if not create:
            return

        if extracted:
            for category in extracted:
                obj.dimension_categories.add(category)
            obj.save()
