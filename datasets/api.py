from __future__ import annotations

from modeltrans.conf import get_available_languages
from modeltrans.translator import get_i18n_field
from modeltrans.utils import build_localized_fieldname
from rest_framework import permissions, serializers, viewsets
from rest_framework.fields import Field
from rest_framework.pagination import PageNumberPagination
from rest_framework.routers import DefaultRouter, SimpleRouter

from rest_framework_nested.routers import NestedSimpleRouter

from .models import DataPoint, Dataset, DatasetSchema, Dimension, DimensionCategory, DatasetMetric, DataPointComment, DataSource, DatasetSourceReference, DatasetSchemaDimension
from django.contrib.contenttypes.models import ContentType

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
    value = serializers.DecimalField(max_digits=10, decimal_places=4, coerce_to_string=False, allow_null=True)

    class Meta:
        model = DataPoint
        fields = ['uuid', 'dataset', 'dimension_categories', 'date', 'value', 'metric']

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
        allowed_metrics = dataset.schema.metrics.all()
        assert metric in allowed_metrics
        return data_point


class DataPointViewSet(viewsets.ModelViewSet):
    pagination_class = PageNumberPagination
    lookup_field = 'uuid'
    serializer_class = DataPointSerializer
    permission_classes = (
        permissions.DjangoModelPermissions,
    )

    def get_queryset(self):
        return DataPoint.objects.filter(dataset__uuid=self.kwargs['dataset_uuid'])

    def perform_create(self, serializer):
        dataset_uuid = self.kwargs['dataset_uuid']
        dataset = Dataset.objects.get(uuid=dataset_uuid)
        serializer.save(dataset=dataset)


class DatasetMetricSerializer(I18nFieldSerializerMixin, serializers.ModelSerializer):
    schema = serializers.SlugRelatedField(slug_field='uuid', read_only=True)
    label = serializers.CharField(source='label_i18n')
    unit = serializers.CharField(source='unit_i18n', required=False)

    class Meta:
        model = DatasetMetric
        fields = ['uuid', 'schema', 'label', 'unit', 'order']


class DatasetMetricViewSet(viewsets.ModelViewSet):
    lookup_field = 'uuid'
    serializer_class = DatasetMetricSerializer
    permission_classes = (
        permissions.DjangoModelPermissions,
    )

    def get_queryset(self):
        return DatasetMetric.objects.filter(schema__uuid=self.kwargs['datasetschema_uuid'])

    def perform_create(self, serializer):
        schema_uuid = self.kwargs['datasetschema_uuid']
        schema = DatasetSchema.objects.get(uuid=schema_uuid)
        serializer.save(schema=schema)


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
        fields = ['uuid', 'time_resolution', 'unit', 'name', 'dimensions', 'metrics', 'start_date']


class DatasetSchemaViewSet(viewsets.ModelViewSet):
    queryset = DatasetSchema.objects.all()
    lookup_field = 'uuid'
    serializer_class = DatasetSchemaSerializer
    permission_classes = (
        permissions.DjangoModelPermissions,
    )


class DatasetSerializer(I18nFieldSerializerMixin, serializers.ModelSerializer):
    data_points: Field = serializers.SlugRelatedField(slug_field='uuid', read_only=True, many=True)
    schema = serializers.SlugRelatedField(slug_field='uuid', queryset=DatasetSchema.objects.all())

    class Meta:
        model = Dataset
        fields = ['uuid', 'schema', 'data_points', 'scope_id', 'scope_content_type']


class DatasetViewSet(viewsets.ModelViewSet):
    queryset = Dataset.objects.all()
    lookup_field = 'uuid'
    serializer_class = DatasetSerializer
    permission_classes = (
        permissions.DjangoModelPermissions,
    )


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


class DataPointCommentSerializer(serializers.ModelSerializer):
    datapoint = serializers.SlugRelatedField(slug_field='uuid', read_only=True)

    class Meta:
        model = DataPointComment
        fields = ['uuid', 'datapoint', 'text', 'type', 'review_state', 'resolved_at', 'resolved_by',
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
        return DataPointComment.objects.filter(datapoint__uuid=self.kwargs['datapoint_uuid'])

    def perform_create(self, serializer):
        datapoint_uuid = self.kwargs['datapoint_uuid']
        datapoint = DataPoint.objects.get(uuid=datapoint_uuid)
        serializer.save(
            datapoint=datapoint,
            created_by=self.request.user,
            last_modified_by=self.request.user
        )

    def perform_update(self, serializer):
        serializer.save(last_modified_by=self.request.user)


class DatasetCommentsViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DataPointCommentSerializer
    permission_classes = (
        permissions.DjangoModelPermissions,
    )

    def get_queryset(self):
        return DataPointComment.objects.filter(
            datapoint__dataset__uuid=self.kwargs['dataset_uuid']
        ).select_related('datapoint', 'created_by', 'last_modified_by', 'resolved_by')


class DatasetSourceReferenceSerializer(serializers.ModelSerializer):
    data_source = serializers.SlugRelatedField(slug_field='uuid', queryset=DataSource.objects.all())
    datapoint = serializers.SlugRelatedField(slug_field='uuid', queryset=DataPoint.objects.all(), required=False)
    dataset = serializers.SlugRelatedField(slug_field='uuid', queryset=Dataset.objects.all(), required=False)

    class Meta:
        model = DatasetSourceReference
        fields = ['datapoint', 'dataset', 'data_source']

    def validate(self, data):
        """
        Check that exactly one of datapoint or dataset is provided.
        """
        datapoint = data.get('datapoint')
        dataset = data.get('dataset')

        if bool(datapoint) == bool(dataset):
            raise serializers.ValidationError("Exactly one of datapoint or dataset must be provided")

        return data


class DatasetSourceReferenceViewSet(viewsets.ModelViewSet):
    lookup_field = 'uuid'
    serializer_class = DatasetSourceReferenceSerializer
    permission_classes = (
        permissions.DjangoModelPermissions,
    )

    def get_queryset(self):
        if 'datapoint_uuid' in self.kwargs:
            return DatasetSourceReference.objects.filter(datapoint__uuid=self.kwargs['datapoint_uuid'])
        elif 'dataset_uuid' in self.kwargs:
            return DatasetSourceReference.objects.filter(dataset__uuid=self.kwargs['dataset_uuid'])
        return DatasetSourceReference.objects.none()

    def perform_create(self, serializer):
        if 'datapoint_uuid' in self.kwargs:
            datapoint = DataPoint.objects.get(uuid=self.kwargs['datapoint_uuid'])
            serializer.save(datapoint=datapoint, dataset=None)
        elif 'dataset_uuid' in self.kwargs:
            dataset = Dataset.objects.get(uuid=self.kwargs['dataset_uuid'])
            serializer.save(dataset=dataset, datapoint=None)


class DataSourceSerializer(serializers.ModelSerializer):
    label = serializers.SerializerMethodField()

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
            )

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
        queryset = DataSource.objects.all()
        if 'uuid' in self.kwargs:
            return queryset

        content_type_app = self.request.query_params.get('content_type_app')
        content_type_model = self.request.query_params.get('content_type_model')
        object_id = self.request.query_params.get('object_id')

        if content_type_app and content_type_model and object_id:
            try:
                content_type = ContentType.objects.get(
                    app_label=content_type_app,
                    model=content_type_model
                )
                queryset = queryset.filter(
                    scope_content_type=content_type,
                    scope_id=object_id
                )
                return queryset
            except ContentType.DoesNotExist:
                return DataSource.objects.none()

        return DataSource.objects.none()


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

datapoint_router.register(r'sources', DatasetSourceReferenceViewSet, basename='datapointsource')
dataset_router.register(r'sources', DatasetSourceReferenceViewSet, basename='datasetsource')

router.register(r'data_sources', DataSourceViewSet, basename='datasource')

all_routers.append(dataset_router)
all_routers.append(dimension_router)
all_routers.append(datasetschema_router)
all_routers.append(datapoint_router)
