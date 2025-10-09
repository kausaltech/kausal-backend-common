from __future__ import annotations

import typing

# from django.contrib.auth.models import AnonymousUser
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from modeltrans.conf import get_available_languages
from modeltrans.translator import get_i18n_field
from modeltrans.utils import build_localized_fieldname
from rest_framework import permissions, serializers, viewsets
from rest_framework.pagination import PageNumberPagination
from rest_framework.routers import DefaultRouter, SimpleRouter

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework_nested.routers import NestedSimpleRouter

from kausal_common.users import user_or_anon, user_or_bust

# from users.models import User
from .models import (
    DataPoint,
    DataPointComment,
    Dataset,
    DatasetMetric,
    DatasetSchema,
    DatasetSchemaDimension,
    DatasetSourceReference,
    DataSource,
    Dimension,
    DimensionCategory,
)

if typing.TYPE_CHECKING:
    from rest_framework.fields import Field

router = DefaultRouter()
all_routers: list[SimpleRouter]  = []


class I18nFieldSerializerMixin:
    Meta: object
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        i18n_field = get_i18n_field(self.Meta.model)  # type: ignore[attr-defined]
        if i18n_field:
            for source_field in i18n_field.fields:
                if source_field not in self.Meta.fields:  # type: ignore[attr-defined]
                    continue
                # When reading, serialize the field using `<x>_i18n` to display the value in currently active language.
                current_language_field = build_localized_fieldname(source_field, 'i18n')
                self.fields[source_field] = serializers.CharField(  # type: ignore[attr-defined]
                    source=current_language_field, read_only=True,
                )
                # Require language to be explicit when writing to a translatable field. That is, when writing, we expect
                # that `<x>_en` is present, for example; `<x>` should not work.
                for lang in get_available_languages():
                    translated_field = build_localized_fieldname(source_field, lang)
                    self.fields[translated_field] = serializers.CharField(  # type: ignore[attr-defined]
                        write_only=True, required=False,
                    )


class DimensionCategorySerializer(I18nFieldSerializerMixin, serializers.ModelSerializer[DimensionCategory]):
    dimension = serializers.SlugRelatedField(slug_field='uuid', read_only=True)  # type: ignore[var-annotated]
    label = serializers.CharField(source='label_i18n')  # type: ignore[assignment]

    class Meta:
        model = DimensionCategory
        fields = ['uuid', 'label', 'dimension']


class DataPointSerializer(serializers.ModelSerializer):
    dataset: Field = serializers.SlugRelatedField(slug_field='uuid', read_only=True)
    dimension_categories = serializers.SlugRelatedField(
        # FIXME: Restrict queryset to dimension categories available to the dataset
        slug_field='uuid', many=True, queryset=DimensionCategory.objects.all(),
    )
    metric = serializers.SlugRelatedField(
        slug_field='uuid', many=False, queryset=DatasetMetric.objects.all()
    )
    value = serializers.DecimalField(max_digits=32, decimal_places=16, coerce_to_string=False, allow_null=True)

    class Meta:
        model = DataPoint
        fields = ['uuid', 'dataset', 'dimension_categories', 'date', 'value', 'metric']

    def validate(self, data):
        """Validate that no duplicate data point exists with the same date, dimension category, and metric combination."""
        date = data.get('date')
        dimension_categories = data.get('dimension_categories')
        metric = data.get('metric')
        dataset = self.context['view'].kwargs.get('dataset_uuid')

        if not all([date, dimension_categories, metric, dataset]):
            return data

        # Skip validation on update (when we have an instance)
        if self.instance:
            return data

        # For each data point, find all points in the same dataset with the same date
        # based on the resolution
        dataset_object = Dataset.objects.get(uuid=dataset)
        schema = dataset_object.schema
        assert schema is not None
        if schema.time_resolution != schema.TimeResolution.YEARLY:
            raise ValueError('Only yearly time resolution supported currently.')
        existing_points = DataPoint.objects.filter(
            dataset__uuid=dataset,
            date__year=date.year,
            metric=metric,
        ).prefetch_related('dimension_categories')

        if not existing_points.exists():
            return data

        dimension_category_uuids = set(dc.uuid for dc in dimension_categories)

        for point in existing_points:
            point_categories = set(dc.uuid for dc in point.dimension_categories.all())
            if point_categories == dimension_category_uuids:
                raise serializers.ValidationError(
                    "A data point with this date, dimension category, and metric combination already exists."
                )

        return data

    def create(self, validated_data):
        dimension_categories = validated_data.pop('dimension_categories')
        data_point = super().create(validated_data)
        dataset = data_point.dataset
        assert dataset == validated_data['dataset']

        schema_dimensions = list(dataset.schema.dimensions.all())
        categories_lists = [schema_dimension.dimension.categories.all() for schema_dimension in schema_dimensions]
        allowed_dimension_categories = [category for categories_list in categories_lists for category in categories_list]
        for dimension_category in dimension_categories:
            # TODO: Do proper validation instead
            assert dimension_category in allowed_dimension_categories
            data_point.dimension_categories.add(dimension_category)
        metric = validated_data.pop('metric')
        assert metric in dataset.schema.metrics.all()
        return data_point


class DataPointViewSet(viewsets.ModelViewSet):
    pagination_class = PageNumberPagination
    lookup_field = 'uuid'
    serializer_class = DataPointSerializer
    permission_classes = (
        permissions.DjangoModelPermissions,
    )

    def get_queryset(self):
        # assert isinstance(self.request.user, User | AnonymousUser)  # to satisfy type checker
        # TODO: check that we don't allow editing instances for which we only have view permissions
        user = user_or_anon(self.request.user)
        qs = DataPoint.permission_policy().instances_user_has_permission_for(user, 'view')
        return qs.filter(dataset__uuid=self.kwargs['dataset_uuid'])

    def perform_create(self, serializer):
        dataset_uuid = self.kwargs['dataset_uuid']
        dataset = Dataset.objects.get(uuid=dataset_uuid)
        user = user_or_bust(self.request.user)
        serializer.save(dataset=dataset, last_modified_by=user)
        dataset.last_modified_by = user
        dataset.save()
        dataset.clear_scope_instance_cache()


    def perform_update(self, serializer):
        user = self.request.user
        instance = serializer.save(last_modified_by=user)
        dataset = instance.dataset
        dataset.last_modified_by = self.request.user
        dataset.save()
        dataset.clear_scope_instance_cache()

    def perform_destroy(self, instance):
        dataset = instance.dataset
        dataset.last_modified_by = self.request.user
        dataset.save()
        dataset.clear_scope_instance_cache()

        instance.delete()


class DatasetMetricSerializer(I18nFieldSerializerMixin, serializers.ModelSerializer):
    schema: serializers.SlugRelatedField[DatasetSchema] = serializers.SlugRelatedField(slug_field='uuid', read_only=True)  # pyright: ignore
    label = serializers.CharField(source='label_i18n')  # type: ignore[assignment]
    unit = serializers.CharField(source='unit_i18n', required=False)

    class Meta:
        model = DatasetMetric
        fields = ['uuid', 'schema', 'label', 'unit', 'order']


class DatasetMetricViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = DatasetMetric.objects.all()
    lookup_field = 'uuid'
    serializer_class = DatasetMetricSerializer
    permission_classes = (
        permissions.DjangoModelPermissions,
    )


class DimensionSerializer(I18nFieldSerializerMixin, serializers.ModelSerializer):
    categories = DimensionCategorySerializer(many=True, required=False)
    name = serializers.CharField(source='name_i18n')

    class Meta:
        model = Dimension
        fields = ['uuid', 'name', 'categories']


class DatasetSchemaDimensionSerializer(serializers.ModelSerializer):
    dimension = DimensionSerializer(many=False, required=False)

    class Meta:
        model = DatasetSchemaDimension
        fields = ['order', 'dimension']


class DatasetSchemaSerializer(I18nFieldSerializerMixin, serializers.ModelSerializer):
    dimensions = DatasetSchemaDimensionSerializer(
        many=True, required=False,
    )
    metrics = DatasetMetricSerializer(many=True, required=False, read_only=True)

    class Meta:
        model = DatasetSchema
        fields = ['uuid', 'time_resolution', 'name', 'dimensions', 'metrics', 'start_date']


class DatasetSchemaViewSet(viewsets.ModelViewSet[DatasetSchema]):
    lookup_field = 'uuid'
    serializer_class = DatasetSchemaSerializer
    permission_classes = (
        permissions.DjangoModelPermissions,
    )

    def get_queryset(self):
        # assert isinstance(self.request.user, User | AnonymousUser)  # to satisfy type checker
        # TODO: check that we don't allow editing instances for which we only have view permissions
        user = user_or_anon(self.request.user)
        return DatasetSchema.permission_policy().instances_user_has_permission_for(user, 'view')

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.datasets.exists():
            raise serializers.ValidationError(
                'Other resources have references to this dataset schema. Please delete those other resources first.'
            )
        return super().destroy(request, *args, **kwargs)


class DatasetScopeContentTypeField(serializers.StringRelatedField):
    def to_internal_value(self, data):
        app_label, model = data
        content_type = ContentType.objects.get(app_label=app_label, model=model)
        return content_type.pk


class DatasetSerializer(I18nFieldSerializerMixin, serializers.ModelSerializer):
    data_points: Field = serializers.SlugRelatedField(slug_field='uuid', read_only=True, many=True)
    schema = serializers.SlugRelatedField(slug_field='uuid', queryset=DatasetSchema.objects.all())
    scope_content_type = DatasetScopeContentTypeField()

    class Meta:
        model = Dataset
        fields = ['uuid', 'schema', 'data_points', 'scope_id', 'scope_content_type']


class DatasetViewSet(viewsets.ModelViewSet):
    lookup_field = 'uuid'
    serializer_class = DatasetSerializer
    permission_classes = (
        permissions.DjangoModelPermissions,
    )

    def get_queryset(self):
        # assert isinstance(self.request.user, User | AnonymousUser)  # to satisfy type checker
        # TODO: check that we don't allow editing instances for which we only have view permissions
        user = user_or_anon(self.request.user)
        return Dataset.permission_policy().instances_user_has_permission_for(user, 'view')


class DimensionViewSet(viewsets.ModelViewSet):
    queryset = Dimension.objects.all()
    lookup_field = 'uuid'
    serializer_class = DimensionSerializer
    permission_classes = (
        permissions.DjangoModelPermissions,
    )


class DimensionCategoryViewSet(viewsets.ModelViewSet):
    lookup_field = 'uuid'
    serializer_class = DimensionCategorySerializer
    permission_classes = (
        permissions.DjangoModelPermissions,
    )

    def get_queryset(self):
        return DimensionCategory.objects.filter(dimension__uuid=self.kwargs['dimension_uuid'])

    def perform_create(self, serializer):
        dimension_uuid = self.kwargs['dimension_uuid']
        dimension = Dimension.objects.get(uuid=dimension_uuid)
        serializer.save(dimension=dimension)

class UserSerializer(serializers.Serializer):
     full_name = serializers.SerializerMethodField()

     def get_full_name(self, instance):
         return instance.get_full_name()

class DataPointCommentSerializer(serializers.ModelSerializer):
    data_point: serializers.SlugRelatedField[DataPoint] = serializers.SlugRelatedField(slug_field='uuid', read_only=True)  # pyright: ignore
    created_by = UserSerializer(read_only=True)
    last_modified_by = UserSerializer(read_only=True)
    resolved_by = UserSerializer(read_only=True)

    class Meta:
        model = DataPointComment
        fields = ['uuid', 'data_point', 'text', 'type', 'review_state', 'resolved_at', 'resolved_by',
                 'created_at', 'created_by', 'last_modified_at', 'last_modified_by']
        read_only_fields = ['uuid', 'resolved_at', 'resolved_by', 'created_at', 'created_by',
                           'last_modified_at', 'last_modified_by']

class DataPointCommentViewSet(viewsets.ModelViewSet):
    lookup_field = 'uuid'
    serializer_class = DataPointCommentSerializer
    permission_classes = (
        permissions.DjangoModelPermissions,
    )

    def get_queryset(self):
        return DataPointComment.objects.filter(data_point__uuid=self.kwargs['datapoint_uuid'])

    def perform_create(self, serializer):
        data_point_uuid = self.kwargs['datapoint_uuid']
        data_point = DataPoint.objects.get(uuid=data_point_uuid)
        serializer.save(
            data_point=data_point,
            created_by=self.request.user,
            last_modified_by=self.request.user
        )

    def perform_update(self, serializer):
        serializer.save(last_modified_by=self.request.user)


class DatasetCommentsViewSet(viewsets.ReadOnlyModelViewSet):
    pagination_class = None
    serializer_class = DataPointCommentSerializer
    permission_classes = (
        permissions.DjangoModelPermissions,
    )

    def get_queryset(self):
        return DataPointComment.objects.filter(
            data_point__dataset__uuid=self.kwargs['dataset_uuid']
        ).select_related('data_point', 'created_by', 'last_modified_by', 'resolved_by')

class BaseSourceReferenceSerializer(serializers.ModelSerializer):
    data_point = serializers.SlugRelatedField(slug_field='uuid', queryset=DataPoint.objects.all(), required=False)
    dataset = serializers.SlugRelatedField(slug_field='uuid', queryset=Dataset.objects.all(), required=False)
    data_source = serializers.SlugRelatedField(slug_field='uuid', queryset=DataSource.objects.all())

    def to_internal_value(self, data: _DT) -> _VT:
        # The parameters in the context come from the API endpoint URL
        dataset_uuid = self.context.get('dataset_uuid')
        data_point_uuid = self.context.get('datapoint_uuid')

        if dataset_uuid != data.get('dataset', dataset_uuid):
            raise serializers.ValidationError(
                'Dataset UUID in payload different from that in the URL path'
            )
        if data_point_uuid != data.get('datapoint', data_point_uuid):
            raise serializers.ValidationError(
                'DataPoint UUID in payload different from that in the URL path'
            )

        if dataset_uuid:
            data['dataset'] = dataset_uuid
        if data_point_uuid:
            data['data_point'] = data_point_uuid
        return super().to_internal_value(data)

    def validate(self, data):
        """
        """
        if 'data_point' not in data and 'dataset' not in data:
            raise serializers.ValidationError("Please supply either data_point or dataset as reference target")
        return data

    class Meta:
        model = DatasetSourceReference
        fields = ['uuid', 'data_point', 'dataset', 'data_source']

class DataPointSourceReferenceViewSet(viewsets.ModelViewSet):
    pagination_class = None
    lookup_field = 'uuid'
    serializer_class = BaseSourceReferenceSerializer
    permission_classes = (permissions.DjangoModelPermissions,)

    def get_queryset(self):
        return DatasetSourceReference.objects.filter(
            data_point__uuid=self.kwargs['datapoint_uuid']
        ).select_related('data_source')

    def get_serializer_context(self) -> dict[str, str]:
        context = super().get_serializer_context()
        context['dataset_uuid'] = self.kwargs['dataset_uuid']
        context['data_point_uuid'] = self.kwargs['datapoint_uuid']
        return context

class DatasetSourceReferenceViewSet(viewsets.ModelViewSet):
    pagination_class = None
    lookup_field = 'uuid'
    serializer_class = BaseSourceReferenceSerializer
    permission_classes = (permissions.DjangoModelPermissions,)

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='reference_target',
                description=(
                    "Type of entity the sources are linked to ('dataset', 'data_point', or 'all'). "
                    "Defaults to 'dataset'."
                ),
                type=OpenApiTypes.STR,
                enum=['dataset', 'data_point', 'all'],
                default='dataset',
                required=False
            )
        ],
        description="List all sources for a dataset with optional filtering by reference target."
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        dataset_uuid = self.kwargs['dataset_uuid']
        reference_target = self.request.query_params.get('reference_target', 'dataset')

        if reference_target == 'data_point':
            return DatasetSourceReference.objects.filter(
                data_point__dataset__uuid=dataset_uuid
            ).select_related('data_point', 'data_source')
        if reference_target == 'all':
            return DatasetSourceReference.objects.filter(
                Q(dataset__uuid=dataset_uuid) |
                Q(data_point__dataset__uuid=dataset_uuid)
            ).select_related('data_point', 'data_source')
        return DatasetSourceReference.objects.filter(dataset__uuid=dataset_uuid)

    def get_serializer_context(self) -> dict[str, str]:
        context = super().get_serializer_context()
        context['dataset_uuid'] = self.kwargs.get('dataset_uuid')
        context['data_point_uuid'] = self.kwargs.get('datapoint_uuid')
        return context



class DataSourceSerializer(serializers.ModelSerializer):
    label = serializers.SerializerMethodField()  # type: ignore[assignment]

    content_type_app = serializers.CharField(write_only=True, required=True)
    content_type_model = serializers.CharField(write_only=True, required=True)
    object_id = serializers.IntegerField(write_only=True, required=True)

    def get_label(self, instance):
        return instance.get_label()

    def create(self, validated_data):
        content_type_app = validated_data.pop('content_type_app', None)
        content_type_model = validated_data.pop('content_type_model', None)
        object_id = validated_data.pop('object_id', None)

        try:
            content_type = ContentType.objects.get(
                app_label=content_type_app,
                model=content_type_model
            )
        except ContentType.DoesNotExist:
            raise serializers.ValidationError(
                f"ContentType with app_label={content_type_app} and model={content_type_model} does not exist"
            ) from None

        data_source = DataSource.objects.create(
            **validated_data,
            scope_content_type=content_type,
            scope_id=object_id
        )

        return data_source

    class Meta:
        model = DataSource
        fields = [
            'uuid', 'name', 'edition', 'authority', 'description', 'url', 'label',
            'content_type_app', 'content_type_model', 'object_id'
        ]
        read_only_fields = ['uuid']


class DataSourceViewSet(viewsets.ModelViewSet):
    lookup_field = 'uuid'
    serializer_class = DataSourceSerializer
    permission_classes = (permissions.DjangoModelPermissions,)

    def get_queryset(self):
        content_type_app = self.request.query_params.get('content_type_app')
        content_type_model = self.request.query_params.get('content_type_model')
        object_id = self.request.query_params.get('object_id')
        has_any_scope_param = any([content_type_app, content_type_model, object_id])
        has_all_scope_params = all([content_type_app, content_type_model, object_id])
        if has_any_scope_param and not has_all_scope_params:
            raise Exception("Must specify either all or none of content_type_app, content_type_model and object_id")

        object_id = typing.cast('str', object_id)
        user = user_or_anon(self.request.user)
        qs = DataSource.permission_policy().instances_user_has_permission_for(user, 'view')

        if has_any_scope_param:
            # Deliberately not catching ContentType.DoesNotExist because this should cause an HTTP error code IMO
            content_type = ContentType.objects.get(
                app_label=content_type_app,
                model=content_type_model
            )
            qs = qs.filter(
                scope_content_type=content_type,
                scope_id=object_id,
            )

        if 'uuid' in self.kwargs:
            qs = qs.filter(uuid=self.kwargs['uuid'])
        return qs


router.register(r'dataset_schemas', DatasetSchemaViewSet, basename='datasetschema')
router.register(r'datasets', DatasetViewSet, basename='dataset')
router.register(r'dimensions', DimensionViewSet, basename='dimension')

dataset_router = NestedSimpleRouter(router, r'datasets', lookup='dataset')
dimension_router = NestedSimpleRouter(router, r'dimensions', lookup='dimension')

dataset_router.register(r'data_points', DataPointViewSet, basename='datapoint')
dimension_router.register(r'categories', DimensionCategoryViewSet, basename='category')

datasetschema_router = NestedSimpleRouter(router, r'dataset_schemas', lookup='datasetschema')
datasetschema_router.register(r'metrics', DatasetMetricViewSet, basename='datasetmetric')

datapoint_router = NestedSimpleRouter(dataset_router, r'data_points', lookup='datapoint')
datapoint_router.register(r'comments', DataPointCommentViewSet, basename='datapointcomment')
dataset_router.register(r'comments', DatasetCommentsViewSet, basename='datasetcomment')

datapoint_router.register(r'sources', DataPointSourceReferenceViewSet, basename='datapointsource')
dataset_router.register(r'sources', DatasetSourceReferenceViewSet, basename='datasetsource')

router.register(r'data_sources', DataSourceViewSet, basename='datasource')

all_routers.append(dataset_router)
all_routers.append(dimension_router)
all_routers.append(datasetschema_router)
all_routers.append(datapoint_router)
