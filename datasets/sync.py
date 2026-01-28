from __future__ import annotations

import csv
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypedDict
from uuid import UUID, uuid4

from django.contrib.postgres.expressions import ArraySubquery
from django.db import models, transaction
from django.db.models import Value
from django.db.models.expressions import Case, F, OuterRef, When
from django.db.utils import IntegrityError
from pydantic import Field

from kausal_common.models.django_pydantic import DjangoAdapter, DjangoDiffModel, JSONAdapter, TypedAdapter

from .models import (
    DataPoint,
    DataPointComment,
    DataPointDimensionCategory,
    Dataset,
    DatasetMetric,
    DatasetSchema,
    DatasetSchemaDimension,
    DatasetSchemaQuerySet,
    DatasetSchemaScope,
    DatasetSourceReference,
    DataSource,
    Dimension,
    DimensionCategory,
    DimensionQuerySet,
    DimensionScope,
)

if TYPE_CHECKING:
    from django.db.models import QuerySet

    from .models import DatasetSchemaScopeType, DimensionScopeType


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
        dim = adapter.get(DimensionModel, str(kwargs.pop('dimension')))
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
    def get_queryset(cls, scope: DimensionScopeType) -> QuerySet[Dimension, dict[str, Any]]:
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
    def get_queryset(cls, scope: DatasetSchemaScopeType) -> QuerySet[DatasetMetric, dict[str, Any]]:
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
        schema = adapter.get(DatasetSchemaModel, str(kwargs.pop('ds_schema')))
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
    def get_queryset(cls, scope: DatasetSchemaScopeType) -> QuerySet[DatasetSchema, dict[str, Any]]:
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
    _children = {
        'data_point_comment': 'comments',
    }

    class DimensionCategoryData(TypedDict):
        uuid: str

    dataset: UUID
    metric_uuid: UUID  # We'll reference metric by UUID
    dimension_categories: list[UUID] = Field(default_factory=list)
    comments: list[UUID] = Field(default_factory=list)

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


class DataPointCommentModel(DjangoDiffModel[DataPointComment]):
    _model = DataPointComment
    _modelname = 'data_point_comment'
    _identifiers = ('uuid',)
    _attributes = (
        'text', 'is_sticky', 'is_review', 'review_state', 'resolved_at', 'data_point',
        'created_at', 'created_by', 'last_modified_by', 'resolved_by',
        'is_soft_deleted', 'soft_deleted_at', 'soft_deleted_by'
    )
    _parent_key = 'data_point'
    _parent_type = 'data_point'

    data_point: UUID

    @classmethod
    def get_queryset(cls, scope: DatasetSchemaScopeType) -> QuerySet[DataPointComment, dict[str, Any]]:
        schemas = DatasetSchema.objects.get_queryset().for_scope(scope)
        datasets = Dataset.objects.filter(schema__in=schemas)
        data_points = DataPoint.objects.filter(dataset__in=datasets)
        comment_fields = cls._django_fields.field_names - {'data_point', 'created_by', 'last_modified_by', 'resolved_by', 'soft_deleted_by'}
        comments = (
            DataPointComment.objects.filter(data_point__in=data_points)
            .values(*comment_fields)
            .annotate(_instance_pk=F('pk'))
            .annotate(data_point=F('data_point__uuid'))
            .annotate(created_by=F('created_by_id'))
            .annotate(last_modified_by=F('last_modified_by_id'))
            .annotate(resolved_by=F('resolved_by_id'))
            .annotate(soft_deleted_by=F('soft_deleted_by_id'))
            .order_by('data_point', '-created_at')
        )
        return comments

    @classmethod
    def get_create_kwargs(cls, adapter: DjangoAdapter, ids: dict, attrs: dict) -> dict:
        kwargs = super().get_create_kwargs(adapter, ids, attrs)
        data_point = adapter.get(DataPointModel, str(kwargs.pop('data_point')))
        assert data_point._instance_pk is not None
        kwargs['data_point_id'] = data_point._instance_pk
        
        # Handle user references - they are stored as IDs, convert None strings to None
        for user_field in ['created_by', 'last_modified_by', 'resolved_by', 'soft_deleted_by']:
            if user_field in kwargs:
                val = kwargs[user_field]
                if val is None or val == '':
                    kwargs[user_field] = None
                else:
                    # Keep as ID (integer)
                    kwargs[user_field + '_id'] = val
                    kwargs.pop(user_field, None)
        
        return kwargs


class DataSourceModel(ScopeAwareDjangoDiffModel[DataSource]):
    _model = DataSource
    _modelname = 'data_source'
    _identifiers = ('uuid',)
    _attributes = ('name', 'edition', 'authority', 'description', 'url')

    @classmethod
    def get_queryset(cls, scope: DatasetSchemaScopeType) -> QuerySet[DataSource, dict[str, Any]]:
        from django.contrib.contenttypes.models import ContentType
        from nodes.models import InstanceConfig
        
        # Get ContentType for InstanceConfig
        ct = ContentType.objects.get_for_model(InstanceConfig)
        
        # Get the instance config ID from scope
        if isinstance(scope, InstanceConfig):
            scope_id = scope.pk
        else:
            # Try to get scope_id from the scope object
            scope_id = getattr(scope, 'pk', None)
            if scope_id is None:
                return DataSource.objects.none().values()
        
        source_fields = cls._django_fields.field_names
        sources = (
            DataSource.objects.filter(scope_content_type=ct, scope_id=scope_id)
            .values(*source_fields)
            .annotate(_instance_pk=F('pk'))
        )
        return sources


class DatasetSourceReferenceModel(DjangoDiffModel[DatasetSourceReference]):
    _model = DatasetSourceReference
    _modelname = 'dataset_source_reference'
    _identifiers = ('uuid',)
    _attributes = ('data_point', 'dataset', 'data_source')

    data_point: UUID | None = None
    dataset: UUID | None = None
    data_source: UUID

    @classmethod
    def get_queryset(cls, scope: DatasetSchemaScopeType) -> QuerySet[DatasetSourceReference, dict[str, Any]]:
        schemas = DatasetSchema.objects.get_queryset().for_scope(scope)
        datasets = Dataset.objects.filter(schema__in=schemas)
        data_points = DataPoint.objects.filter(dataset__in=datasets)
        
        ref_fields = cls._django_fields.field_names - {'data_point', 'dataset', 'data_source'}
        references = (
            DatasetSourceReference.objects.filter(
                models.Q(dataset__in=datasets) | models.Q(data_point__in=data_points)
            )
            .values(*ref_fields)
            .annotate(_instance_pk=F('pk'))
            .annotate(
                data_point=Case(
                    When(data_point__isnull=False, then=F('data_point__uuid')),
                    default=Value(None),
                    output_field=models.UUIDField()
                )
            )
            .annotate(
                dataset=Case(
                    When(dataset__isnull=False, then=F('dataset__uuid')),
                    default=Value(None),
                    output_field=models.UUIDField()
                )
            )
            .annotate(data_source=F('data_source__uuid'))
            .order_by('pk')  # Override model's default ordering that uses relationships
        )
        return references

    @classmethod
    def get_create_kwargs(cls, adapter: DjangoAdapter, ids: dict, attrs: dict) -> dict:
        kwargs = super().get_create_kwargs(adapter, ids, attrs)
        
        data_source_uuid = kwargs.pop('data_source')
        data_source = adapter.get(DataSourceModel, str(data_source_uuid))
        assert data_source._instance_pk is not None
        kwargs['data_source_id'] = data_source._instance_pk
        
        data_point_uuid = kwargs.pop('data_point', None)
        if data_point_uuid:
            data_point = adapter.get(DataPointModel, str(data_point_uuid))
            assert data_point._instance_pk is not None
            kwargs['data_point_id'] = data_point._instance_pk
        
        dataset_uuid = kwargs.pop('dataset', None)
        if dataset_uuid:
            dataset = adapter.get(DatasetModel, str(dataset_uuid))
            assert dataset._instance_pk is not None
            kwargs['dataset_id'] = dataset._instance_pk
        
        return kwargs


class DatasetModel(DjangoDiffModel[Dataset]):
    _model = Dataset
    _modelname = 'dataset'
    _identifiers = ('uuid',)
    _attributes = ('identifier', 'ds_schema')
    _children = {
        'data_point': 'data_points',
        'dataset_source_reference': 'source_references',
    }
    _parent_key = 'ds_schema'
    _parent_type = 'dataset_schema'

    ds_schema: UUID
    data_points: list[UUID] = Field(default_factory=list)
    source_references: list[UUID] = Field(default_factory=list)
    uuid: UUID = Field(default_factory=uuid4)

    @classmethod
    def get_queryset(cls, scope: DatasetSchemaScopeType) -> QuerySet[Dataset, dict[str, Any]]:
        schemas = DatasetSchema.objects.get_queryset().for_scope(scope)
        dataset_fields = cls._django_fields.field_names - {'ds_schema'}
        datasets = (
            Dataset.objects.filter(schema__in=schemas)
            .values(*dataset_fields)
            .annotate(_instance_pk=F('pk'))
            .annotate(ds_schema=F('schema__uuid'))
        )
        return datasets

    @classmethod
    def create_related(cls, adapter: DjangoAdapter, _ids: dict, _attrs: dict, _instance: Dataset, /) -> None:
        assert isinstance(adapter, DatasetDjangoAdapter)
        pass

    @classmethod
    def get_create_kwargs(cls, adapter: DjangoAdapter, ids: dict, attrs: dict) -> dict:
        assert isinstance(adapter, DatasetDjangoAdapter)
        kwargs = super().get_create_kwargs(adapter, ids, attrs)
        schema_uuid = kwargs.pop('ds_schema', None)

        if schema_uuid:
            schema = adapter.get(DatasetSchemaModel, str(schema_uuid))
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
    data_point_comment = DataPointCommentModel
    data_source = DataSourceModel
    dataset_source_reference = DatasetSourceReferenceModel
    top_level = ['dimension', 'dataset_schema', 'data_source']


class DatasetDjangoAdapter(DjangoAdapter, DatasetAdapter):
    def __init__(self, scope: DatasetSchemaScopeType, **kwargs):
        super().__init__(**kwargs)
        self.scope = scope

    def load_dimension_categories(self, dims: DimensionQuerySet):
        cats = self.dimension_category.get_queryset(dims)
        for cat_data in cats:
            # Load related objects
            dim = self.get(DimensionModel, str(cat_data['dimension']))
            cat_model = self.dimension_category.from_django(cat_data)
            self.add_child(dim, cat_model)

    def load_dataset_metrics(self, _schema_qs: DatasetSchemaQuerySet):
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

    def load_data_point_comments(self, scope: DatasetSchemaScopeType):
        comments = self.data_point_comment.get_queryset(scope)
        for comment_data in comments:
            comment_model = self.data_point_comment.from_django(comment_data)
            data_point_model = self.get(DataPointModel, str(comment_model.data_point))
            self.add_child(data_point_model, comment_model)

    def load_data_sources(self, scope: DatasetSchemaScopeType):
        sources = self.data_source.get_queryset(scope)
        for source_data in sources:
            source_model = self.data_source.from_django(source_data)
            self.add(source_model)

    def load_dataset_source_references(self, scope: DatasetSchemaScopeType):
        references = self.dataset_source_reference.get_queryset(scope)
        for ref_data in references:
            ref_model = self.dataset_source_reference.from_django(ref_data)
            # Source references can be linked to either dataset or data_point
            if ref_model.dataset:
                dataset_model = self.get(DatasetModel, str(ref_model.dataset))
                self.add_child(dataset_model, ref_model)
            elif ref_model.data_point:
                data_point_model = self.get(DataPointModel, str(ref_model.data_point))
                self.add_child(data_point_model, ref_model)

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

        # Load data sources
        self.load_data_sources(self.scope)

        # Load data point comments
        self.load_data_point_comments(self.scope)

        # Load dataset source references
        self.load_dataset_source_references(self.scope)

    def export_csv(self, output_dir: Path) -> None:  # noqa: C901
        """Export each dataset as a CSV file."""
        output_dir.mkdir(parents=True, exist_ok=True)

        # Get all datasets
        datasets = self.get_all(DatasetModel)

        for dataset_model in datasets:
            dataset_identifier = getattr(dataset_model, 'identifier', None)
            if not dataset_identifier:
                # Skip datasets without identifiers
                continue

            # Get schema
            schema_model = self.get(DatasetSchemaModel, str(dataset_model.ds_schema))

            # Get dimensions for this schema
            schema_dimensions = []
            for dim_uuid in schema_model.dimensions:
                dim_model = self.get(DimensionModel, str(dim_uuid))
                schema_dimensions.append(dim_model)

            # Get all data points for this dataset
            data_points = dataset_model.get_children(DataPointModel)

            if not data_points:
                # Skip empty datasets
                continue

            # Build a mapping: (metric_uuid, tuple of category_uuids) -> {year: value}
            # We need to map dimension categories to their dimensions
            category_to_dimension: dict[str, DimensionModel] = {}
            for dim_model in schema_dimensions:
                dim_categories = dim_model.get_children(DimensionCategoryModel)
                for cat_model in dim_categories:
                    category_to_dimension[str(cat_model.uuid)] = dim_model

            # Group data points by metric and dimension categories
            # Use tuple with optional UUIDs for categories
            grouped_data: dict[tuple[UUID, tuple[UUID | None, ...]], dict[int, str]] = defaultdict(dict)

            for dp_model in data_points:
                metric_uuid = dp_model.metric_uuid

                # Create a mapping of dimension -> category for this data point
                dim_cat_map: dict[UUID, UUID] = {}
                for cat_uuid in dp_model.dimension_categories:
                    cat_uuid_str = str(cat_uuid)
                    if cat_uuid_str in category_to_dimension:
                        dim_model = category_to_dimension[cat_uuid_str]
                        dim_cat_map[dim_model.uuid] = cat_uuid

                # Create a tuple of category UUIDs in the order of schema dimensions
                category_tuple = tuple(
                    dim_cat_map.get(dim_model.uuid) for dim_model in schema_dimensions
                )

                # Extract year from date
                dp_date = getattr(dp_model, 'date', None)
                if dp_date is None:
                    continue
                if isinstance(dp_date, str):
                    # Parse date string
                    year = int(dp_date.split('-')[0])
                elif isinstance(dp_date, date):
                    year = dp_date.year
                else:
                    continue

                # Store value
                key = (metric_uuid, category_tuple)
                dp_value = getattr(dp_model, 'value', None)
                grouped_data[key][year] = str(dp_value) if dp_value is not None else ''

            # Get all unique years
            all_years = sorted(set().union(*(year_dict.keys() for year_dict in grouped_data.values())))

            # Build CSV rows
            rows = []
            for (metric_uuid, category_tuple), year_values in grouped_data.items():
                metric_model = self.get(DatasetMetricModel, str(metric_uuid))
                metric_name = getattr(metric_model, 'name', '') or ''
                metric_unit = getattr(metric_model, 'unit', '') or ''

                row: dict[str, str] = {}

                # Add dimension columns
                for i, dim_model in enumerate(schema_dimensions):
                    cat_uuid = category_tuple[i] if i < len(category_tuple) else None
                    dim_identifier = getattr(dim_model, 'identifier', None) or getattr(dim_model, 'name', '') or ''
                    if cat_uuid:
                        cat_model = self.get(DimensionCategoryModel, str(cat_uuid))
                        cat_identifier = getattr(cat_model, 'identifier', '') or ''
                        row[dim_identifier] = cat_identifier
                    else:
                        row[dim_identifier] = ''

                # Add metric and unit columns
                row['Metric'] = metric_name
                row['Unit'] = metric_unit

                # Add year columns
                for year in all_years:
                    row[str(year)] = year_values.get(year, '')

                rows.append(row)

            # Write CSV file
            if rows:
                # Create filename from dataset identifier
                safe_filename = str(dataset_identifier).replace('/', '_').replace('\\', '_')
                csv_path = output_dir / f"{safe_filename}.csv"

                # Get all column names in order
                fieldnames: list[str] = []
                # Dimension columns
                for dim_model in schema_dimensions:
                    dim_identifier = getattr(dim_model, 'identifier', None) or getattr(dim_model, 'name', '') or ''
                    fieldnames.append(dim_identifier)
                # Metric and Unit columns
                fieldnames.extend(['Metric', 'Unit'])
                # Year columns
                fieldnames.extend(str(year) for year in all_years)

                with csv_path.open('w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(rows)


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

        # Load data sources
        for source_data in data.get('data_source', []):
            source_model = self.data_source.model_validate(source_data)
            self.add(source_model)

        # Load data point comments
        for comment_data in data.get('data_point_comment', []):
            comment_model = self.data_point_comment.model_validate(comment_data)
            data_point_model = self.get(self.data_point, str(comment_model.data_point))
            self.add_child(data_point_model, comment_model)

        # Load dataset source references
        for ref_data in data.get('dataset_source_reference', []):
            ref_model = self.dataset_source_reference.model_validate(ref_data)
            if ref_model.dataset:
                dataset_model = self.get(self.dataset, str(ref_model.dataset))
                self.add_child(dataset_model, ref_model)
            elif ref_model.data_point:
                data_point_model = self.get(self.data_point, str(ref_model.data_point))
                self.add_child(data_point_model, ref_model)
