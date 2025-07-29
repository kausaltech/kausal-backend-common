from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypedDict, cast
from uuid import UUID, uuid4

from django.contrib.postgres.expressions import ArraySubquery
from django.db import models, transaction
from django.db.models.expressions import F, OuterRef
from django.db.models.functions.json import JSONObject
from django.db.utils import IntegrityError
from pydantic import Field

from kausal_common.models.django_pydantic import DjangoAdapter, DjangoDiffModel, JSONAdapter, TypedAdapter

from .models import (
    DataPoint,
    DataPointDimensionCategory,
    Dataset,
    DatasetMetric,
    DatasetSchema,
    DatasetSchemaDimension,
    DatasetSchemaQuerySet,
    DatasetSchemaScope,
    Dimension,
    DimensionCategory,
    DimensionQuerySet,
    DimensionScope,
)

if TYPE_CHECKING:
    from django.db.models import QuerySet

    from .models import ScopeType


class ScopeAwareDjangoDiffModel[M: models.Model](DjangoDiffModel[M]):
    @classmethod
    def create_django_instance(cls, adapter: DjangoAdapter, create_kwargs: dict) -> M:
        try:
            with transaction.atomic():
                obj = super().create_django_instance(adapter, create_kwargs)
        except IntegrityError:
            existing_obj = cls._model._default_manager.filter(uuid=create_kwargs['uuid']).first()
            if not existing_obj:
                raise
            adapter.increase_counter('scope_attachments')
            return existing_obj
        else:
            return obj


class DimensionCategoryModel(ScopeAwareDjangoDiffModel[DimensionCategory]):
    _model = DimensionCategory
    _modelname = 'dimension_category'
    _identifiers = ('uuid',)
    _attributes = ('identifier', 'label', 'dimension')
    _parent_key = 'dimension'
    _parent_type = 'dimension'

    dimension: UUID

    @classmethod
    def get_queryset(cls, dimension_qs: DimensionQuerySet) -> QuerySet[DimensionCategory, dict[str, Any]]:
        cat_fields = cls._django_fields.field_names - {'dimension'}
        categories = (
            DimensionCategory.objects.filter(dimension__in=dimension_qs)
            .values(*cat_fields)
            .annotate(_instance_pk=F('pk'))
            .annotate(dimension=F('dimension__uuid'))
            .order_by('dimension', 'order')
        )
        return categories

    @classmethod
    def get_create_kwargs(cls, adapter: DjangoAdapter, ids: dict, attrs: dict) -> dict:
        kwargs = super().get_create_kwargs(adapter, ids, attrs)
        dim = cast('DimensionModel', adapter.get(DimensionModel, str(kwargs.pop('dimension'))))
        assert dim._instance_pk is not None
        kwargs['dimension_id'] = dim._instance_pk
        return kwargs


# class DimensionScopeModel(DjangoDiffModel[DimensionScope]):
#     _model = DimensionScope
#     _modelname = 'dimension_scope'
#     _identifiers = ('id',)  # Using id since no UUID field
#     _attributes = ('identifier', 'scope_type', 'scope_id', 'dimension')
#     _parent_key = 'dimension'
#     _parent_type = 'dimension'

#     dimension: UUID
#     scope_type: str
#     scope_id: UUID

#     @classmethod
#     def get_queryset(
#         cls, dimension: Dimension, scope: ScopeType
#     ) -> QuerySet[DimensionScope, dict[str, Any]]:
#         scope_fields = cls._django_fields.field_names - {'dimension'}
#         ct = ContentType.objects.get_for_model(type(scope))
#         scopes = (
#             DimensionScope.objects.filter(
#                 dimension=dimension,
#                 scope_content_type_id=ct.id,
#                 scope_id=scope.uuid,
#             )
#             .values(*scope_fields)
#             .annotate(_instance_pk=F('pk'))
#             .annotate(dimension=F('dimension__uuid'))
#             .annotate(scope_type=Value(type(scope)._meta.model_name, output_field=CharField()))
#             .annotate(scope_id=Value(str(scope.uuid), output_field=CharField()))
#             .order_by('order')
#         )
#         return scopes

#     @classmethod
#     def get_create_kwargs(cls, adapter: DjangoAdapter, ids: dict, attrs: dict) -> dict:
#         kwargs = super().get_create_kwargs(adapter, ids, attrs)
#         dim = cast('DimensionModel', adapter.get(DimensionModel, str(kwargs.pop('dimension'))))
#         assert dim._instance_pk is not None
#         kwargs['dimension_id'] = dim._instance_pk
#         return kwargs


class DimensionModel(ScopeAwareDjangoDiffModel[Dimension]):
    _model = Dimension
    _modelname = 'dimension'
    _identifiers = ('uuid',)
    _attributes = ('name', 'identifier')
    _children = {
        'dimension_category': 'categories',
        #'dimension_scope': 'scopes',
    }

    categories: list[UUID] = Field(default_factory=list)
    scopes: list[int] = Field(default_factory=list)  # Using id for scopes
    identifier: str | None = None
    uuid: UUID = Field(default_factory=uuid4)

    @classmethod
    def get_queryset(cls, scope: ScopeType) -> QuerySet[Dimension, dict[str, Any]]:
        dim_fields = list(cls._django_fields.plain_fields.keys())
        dimensions = (
            Dimension.objects.get_queryset().for_scope(scope)
            .distinct()
            .annotate(identifier=F('scopes__identifier'))
            .values(*dim_fields, 'identifier', _instance_pk=F('pk'))
        )
        return dimensions

    @classmethod
    def get_create_kwargs(cls, adapter: DjangoAdapter, ids: dict, attrs: dict) -> dict:
        kwargs = super().get_create_kwargs(adapter, ids, attrs)
        kwargs.pop('identifier')
        return kwargs

    @classmethod
    def create_related(cls, adapter: DatasetDjangoAdapter, _ids: dict, _attrs: dict, instance: Dimension, /) -> None:  # type: ignore[override]
        scope = adapter.scope
        DimensionScope.objects.create(
            dimension=instance,
            scope=scope,
            identifier=_attrs['identifier'],
        )


class DatasetMetricModel(ScopeAwareDjangoDiffModel[DatasetMetric]):
    _model = DatasetMetric
    _modelname = 'dataset_metric'
    _identifiers = ('uuid',)
    _attributes = ('name', 'label', 'unit', 'ds_schema')
    _parent_key = 'ds_schema'
    _parent_type = 'dataset_schema'

    ds_schema: UUID

    @classmethod
    def get_queryset(cls, scope: ScopeType) -> QuerySet[DatasetMetric, dict[str, Any]]:
        schemas = DatasetSchema.objects.get_queryset().for_scope(scope)
        metric_fields = cls._django_fields.field_names - {'ds_schema'}
        metrics = (
            DatasetMetric.objects.filter(schema__in=schemas)
            .values(*metric_fields)
            .annotate(_instance_pk=F('pk'))
            .annotate(ds_schema=F('schema__uuid'))
            .order_by('schema', 'order')
        )
        return metrics

    @classmethod
    def get_create_kwargs(cls, adapter: DjangoAdapter, ids: dict, attrs: dict) -> dict:
        kwargs = super().get_create_kwargs(adapter, ids, attrs)
        schema = cast('DatasetSchemaModel', adapter.get(DatasetSchemaModel, str(kwargs.pop('ds_schema'))))
        assert schema._instance_pk is not None
        kwargs['schema_id'] = schema._instance_pk
        return kwargs


class DatasetSchemaModel(ScopeAwareDjangoDiffModel[DatasetSchema]):
    _model = DatasetSchema
    _modelname = 'dataset_schema'
    _identifiers = ('uuid',)
    _attributes = ('name', 'description', 'time_resolution', 'start_date', 'dimensions')
    _children = {
        'dataset_metric': 'metrics',
        'dataset': 'datasets',
    }

    metrics: list[UUID] = Field(default_factory=list)
    dimensions: list[UUID] = Field(default_factory=list)
    datasets: list[UUID] = Field(default_factory=list)
    uuid: UUID = Field(default_factory=uuid4)

    @classmethod
    def get_queryset(cls, scope: ScopeType) -> QuerySet[DatasetSchema, dict[str, Any]]:
        schema_fields = cls._django_fields.field_names - {'dimensions'}

        # dp_cats = (
        #     DataPointDimensionCategory.objects.filter(
        #         data_point_id=OuterRef('pk'),
        #     )
        #     .annotate(
        #         category=F('dimension_category__uuid'),
        #     )
        #     .values_list('category')
        # )

        # dps = DataPoint.objects.filter(
        #     dataset_id=OuterRef('pk'),
        # ).annotate(data=JSONObject(
        #     date=F('date'), value=F('value'), metric=F('metric__uuid'), dimension_categories=ArraySubquery(dp_cats),
        # )).values_list('data')

        ds_dims = DatasetSchemaDimension.objects.filter(schema=OuterRef('pk')).values_list('dimension__uuid')
        schemas = (
            DatasetSchema.objects.get_queryset().for_scope(scope)
            .values(*schema_fields)
            .annotate(_instance_pk=F('pk'))
            .annotate(dimensions=ArraySubquery(ds_dims))
            # .annotate(data_points=ArraySubquery(dps))
        )
        return schemas

    @classmethod
    def create_related(cls, adapter: DatasetDjangoAdapter, _ids: dict, _attrs: dict, instance: DatasetSchema, /) -> None:  # type: ignore[override]
        scope = adapter.scope
        DatasetSchemaScope.objects.create(
            schema=instance,
            scope=scope,
        )
        dims = []
        for dim in _attrs['dimensions']:
            dim_obj = adapter.get(DimensionModel, str(dim))
            dims.append(DatasetSchemaDimension(schema=instance, dimension_id=dim_obj._instance_pk))

        DatasetSchemaDimension.objects.bulk_create(dims)


class DataPointModel(DjangoDiffModel[DataPoint]):
    _model = DataPoint
    _modelname = 'data_point'
    _identifiers = ('uuid',)
    _attributes = ('date', 'value', 'metric_uuid', 'dataset', 'dimension_categories')
    _parent_key = 'dataset'
    _parent_type = 'dataset'

    class DimensionCategoryData(TypedDict):
        uuid: str

    dataset: UUID
    metric_uuid: UUID  # We'll reference metric by UUID
    dimension_categories: list[UUID] = Field(default_factory=list)

    @classmethod
    def get_queryset(cls, dataset: Dataset) -> QuerySet[DataPoint, dict[str, Any]]:
        # Get dimension categories as JSON array
        dim_cats = (
            DataPointDimensionCategory.objects.filter(
                data_point_id=OuterRef('pk'),
            )
            .annotate(
                category=F('dimension_category__uuid'),
            )
            .values_list('category')
        )

        point_fields = cls._django_fields.field_names - {'dataset', 'metric_uuid', 'dimension_categories'}
        data_points = (
            DataPoint.objects.filter(dataset=dataset)
            .values(*point_fields)
            .annotate(_instance_pk=F('pk'))
            .annotate(dataset=F('dataset__uuid'))
            .annotate(metric_uuid=F('metric__uuid'))
            .annotate(dimension_categories=ArraySubquery(dim_cats))
            .order_by('date')
        )
        return data_points

    @classmethod
    def get_create_kwargs(cls, adapter: DjangoAdapter, ids: dict, attrs: dict) -> dict:
        kwargs = super().get_create_kwargs(adapter, ids, attrs)
        dataset = adapter.get(DatasetModel, str(kwargs.pop('dataset')))

        metric_uuid = kwargs.pop('metric_uuid')
        # Find the metric by UUID
        metric = adapter.get(DatasetMetricModel, str(metric_uuid))

        assert dataset._instance_pk is not None
        kwargs['dataset_id'] = dataset._instance_pk
        kwargs['metric_id'] = metric._instance_pk
        kwargs.pop('dimension_categories')
        return kwargs

    @classmethod
    def create_related(cls, _adapter: DjangoAdapter, _ids: dict, attrs: dict, instance: DataPoint, /) -> None:
        dim_cats = attrs.get('dimension_categories', [])
        if not dim_cats:
            return

        cat_objs = []
        for cat_uuid in dim_cats:
            category = _adapter.get(DimensionCategoryModel, str(cat_uuid))
            assert category._instance_pk is not None
            cat_objs.append(DataPointDimensionCategory(data_point=instance, dimension_category_id=category._instance_pk))
        DataPointDimensionCategory.objects.bulk_create(cat_objs)


class DatasetModel(DjangoDiffModel[Dataset]):
    _model = Dataset
    _modelname = 'dataset'
    _identifiers = ('uuid',)
    _attributes = ('identifier', 'ds_schema')
    _children = {
        'data_point': 'data_points',
    }
    _parent_key = 'ds_schema'
    _parent_type = 'dataset_schema'

    ds_schema: UUID
    data_points: list[UUID] = Field(default_factory=list)
    uuid: UUID = Field(default_factory=uuid4)

    @classmethod
    def get_queryset(cls, scope: ScopeType) -> QuerySet[Dataset, dict[str, Any]]:
        dataset_fields = cls._django_fields.field_names - {'ds_schema'}
        datasets = (
            Dataset.objects.get_queryset().for_scope(scope)
            .values(*dataset_fields)
            .annotate(_instance_pk=F('pk'))
            .annotate(ds_schema=F('schema__uuid'))
        )
        return datasets

    @classmethod
    def create_related(cls, adapter: DjangoAdapter, _ids: dict, _attrs: dict, instance: Dataset, /) -> None:
        assert isinstance(adapter, DatasetDjangoAdapter)
        scope = adapter.scope
        pass

    @classmethod
    def get_create_kwargs(cls, adapter: DjangoAdapter, ids: dict, attrs: dict) -> dict:
        assert isinstance(adapter, DatasetDjangoAdapter)
        kwargs = super().get_create_kwargs(adapter, ids, attrs)
        schema_uuid = kwargs.pop('ds_schema', None)

        if schema_uuid:
            schema = cast('DatasetSchemaModel', adapter.get(DatasetSchemaModel, str(schema_uuid)))
            assert schema._instance_pk is not None
            kwargs['schema_id'] = schema._instance_pk
        kwargs['scope'] = adapter.scope

        return kwargs


class DatasetAdapter(TypedAdapter):
    dimension = DimensionModel
    dimension_category = DimensionCategoryModel
    dataset_schema = DatasetSchemaModel
    dataset_metric = DatasetMetricModel
    dataset = DatasetModel
    data_point = DataPointModel
    top_level = ['dimension', 'dataset_schema']


class DatasetDjangoAdapter(DjangoAdapter, DatasetAdapter):
    def __init__(self, scope: ScopeType, **kwargs):
        super().__init__(**kwargs)
        self.scope = scope

    def load_dimension_categories(self, dims: DimensionQuerySet):
        cats = self.dimension_category.get_queryset(dims)
        for cat_data in cats:
            # Load related objects
            dim = self.get(DimensionModel, str(cat_data['dimension']))
            cat_model = self.dimension_category.from_django(cat_data)
            self.add_child(dim, cat_model)

    def load_dataset_metrics(self, schema_qs: DatasetSchemaQuerySet):
        metrics = self.dataset_metric.get_queryset(scope=self.scope)
        for metric in metrics:
            metric_model = self.dataset_metric.from_django(metric)
            schema_model = self.get(DatasetSchemaModel, str(metric_model.ds_schema))
            self.add_child(schema_model, metric_model)

    def load_data_points(self, dataset: Dataset, dataset_model: DatasetModel):
        data_points = self.data_point.get_queryset(dataset)
        for dp in data_points:
            dp_model = self.data_point.from_django(dp)
            self.add_child(dataset_model, dp_model)

    def load(self) -> None:
        # Load dimensions
        dimensions = self.dimension.get_queryset(self.scope)
        for dim_data in dimensions:
            dim_model = self.dimension.from_django(dim_data)
            self.add(dim_model)

        dims = Dimension.objects.get_queryset().for_scope(self.scope)
        self.load_dimension_categories(dims)

        dataset_schemas = self.dataset_schema.get_queryset(self.scope)
        for schema_obj in dataset_schemas:
            schema_model = DatasetSchemaModel.from_django(schema_obj)
            self.add(schema_model)

        schema_qs = DatasetSchema.objects.get_queryset().for_scope(self.scope)
        self.load_dataset_metrics(schema_qs)

        # Load datasets
        datasets = self.dataset.get_queryset(self.scope)
        for dataset_data in datasets:
            dataset_model = self.dataset.from_django(dataset_data)

            schema_model = self.get(DatasetSchemaModel, str(dataset_model.ds_schema))
            self.add_child(schema_model, dataset_model)

            # Load data points
            dataset_obj = Dataset.objects.get(pk=dataset_data['_instance_pk'])
            self.load_data_points(dataset_obj, dataset_model)


class DatasetJSONAdapter(JSONAdapter, DatasetAdapter):
    def load(self) -> None:
        data = self.load_json()
        assert isinstance(data, dict)

        # Load dimensions
        for dim_data in data.get('dimension', []):
            dim_model = self.dimension.model_validate(dim_data)
            self.add(dim_model)

        # Load dimension categories
        for cat_data in data.get('dimension_category', []):
            cat_model = self.dimension_category.model_validate(cat_data)
            dim_model = self.get(self.dimension, str(cat_model.dimension))
            self.add_child(dim_model, cat_model)

        # Load dataset schemas
        for schema_data in data.get('dataset_schema', []):
            schema_model = self.dataset_schema.model_validate(schema_data)
            self.add(schema_model)

        # Load dataset metrics
        for metric_data in data.get('dataset_metric', []):
            metric_model = self.dataset_metric.model_validate(metric_data)
            schema_model = self.get(self.dataset_schema, str(metric_model.ds_schema))
            self.add_child(schema_model, metric_model)

        # Load datasets
        for dataset_data in data.get('dataset', []):
            dataset_model = self.dataset.model_validate(dataset_data)
            if dataset_model.ds_schema:
                schema_model = self.get(self.dataset_schema, str(dataset_model.ds_schema))
                self.add_child(schema_model, dataset_model)
            else:
                self.add(dataset_model)

        # Load data points
        for dp_data in data.get('data_point', []):
            dp_model = self.data_point.model_validate(dp_data)
            dataset_model = self.get(self.dataset, str(dp_model.dataset))
            self.add_child(dataset_model, dp_model)
