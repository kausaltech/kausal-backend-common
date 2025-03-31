from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, ClassVar, Self

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import gettext_lazy as _
from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel
from modeltrans.fields import TranslationField
from wagtail.admin.panels.field_panel import FieldPanel
from wagtail.admin.panels.inline_panel import InlinePanel

from kausal_common.datasets.permission_policy import get_permission_policy
from kausal_common.models.fields import IdentifierField
from kausal_common.models.permission_policy import ModelPermissionPolicy
from kausal_common.models.uuid import UUIDIdentifiedModel

from ..models.modification_tracking import UserModifiableModel
from ..models.ordered import OrderedModel
from ..models.permissions import PermissionedModel, PermissionedQuerySet
from ..models.types import ModelManager, RevMany
from .config import dataset_config

if TYPE_CHECKING:
    import contextlib
    from typing import Self

    from rich.repr import RichReprResult

    from kausal_common.models.permission_policy import ModelPermissionPolicy
    from kausal_common.models.types import QS

    from users.models import User

    from ..models.types import FK, RevMany
    with contextlib.suppress(ImportError):
        from actions.models import Plan  # type: ignore

        from nodes.models import InstanceConfig  # type: ignore


class DimensionQuerySet(PermissionedQuerySet['Dimension']):
    pass


class DimensionCategoryQuerySet(PermissionedQuerySet['DimensionCategory']):
    pass


class DatasetSchemaQuerySet(PermissionedQuerySet['DatasetSchema']):
    pass


class DatasetMetricQuerySet(PermissionedQuerySet['DatasetMetric']):
    pass


class DatasetSchemaDimensionQuerySet(PermissionedQuerySet['DatasetSchemaDimension']):
    pass


class DatasetSchemaScopeQuerySet(PermissionedQuerySet['DatasetSchemaScope']):
    pass


class DataPointQuerySet(PermissionedQuerySet['DataPoint']):
    pass


class DataPointCommentQuerySet(PermissionedQuerySet['DataPointComment']):
    pass


class DataSourceQuerySet(PermissionedQuerySet['DataSource']):
    pass


class DatasetSourceReferenceQuerySet(PermissionedQuerySet['DatasetSourceReference']):
    pass


class Dimension(ClusterableModel, UUIDIdentifiedModel, UserModifiableModel, PermissionedModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=100, verbose_name=_('name'))

    i18n = TranslationField(fields=['name'])
    name_i18n: str

    scopes: RevMany[DimensionScope]
    objects: ClassVar[DimensionQuerySet] = DimensionQuerySet.as_manager() # pyright: ignore
    _default_manager: ClassVar[DimensionQuerySet]

    class Meta:
        verbose_name = _('dimension')
        verbose_name_plural = _('dimensions')
        ordering = ('name',)

    def __str__(self):
        return self.name_i18n

    def __rich_repr__(self) -> RichReprResult:
        yield 'uuid', self.uuid
        yield 'name', self.name
        scopes = list(self.scopes.all())
        if len(scopes) == 1:
            yield 'scope', scopes[0].scope
        else:
            yield 'scopes', [scope.scope for scope in scopes]


class DimensionCategory(OrderedModel, UUIDIdentifiedModel, UserModifiableModel, PermissionedModel):
    identifier = IdentifierField[str | None, str | None](
        null=True,
        blank=True,
        help_text=_("Optional identifier that, if set, must be unique within the dimension"),
        max_length=200,
    )
    dimension = ParentalKey(Dimension, blank=False, on_delete=models.CASCADE, related_name='categories')
    label = models.CharField(max_length=100, verbose_name=_('label'))

    i18n = TranslationField(fields=['label'])
    label_i18n: str

    objects: ClassVar[DimensionCategoryQuerySet] = DimensionCategoryQuerySet.as_manager() # pyright: ignore
    _default_manager: ClassVar[DimensionCategoryQuerySet]

    class Meta:
        verbose_name = _('dimension category')
        verbose_name_plural = _('dimension categories')
        constraints = (
            models.UniqueConstraint(
                fields=['identifier', 'dimension'],
                name='unique_identifier_per_dimension',
            ),
        )

    def __str__(self) -> str:
        if self.label_i18n:
            return f'{self.label_i18n} ({self.uuid})'
        return str(self.uuid)

    def __rich_repr__(self) -> RichReprResult:
        yield 'uuid', self.uuid
        yield 'label', self.label
        yield 'dimension', self.dimension

    def filter_siblings(self, qs: models.QuerySet[DimensionCategory]) -> models.QuerySet[DimensionCategory]:
        return qs.filter(dimension=self.dimension)


class DimensionScopeQuerySet(PermissionedQuerySet['DimensionScope']):
    def for_instance_config(self, instance_config: InstanceConfig) -> Self:
        return self.filter(scope_content_type=ContentType.objects.get_for_model(instance_config), scope_id=instance_config.pk)


_DimensionScopeManager = models.Manager.from_queryset(DimensionScopeQuerySet)
class DimensionScopeManager(ModelManager['DimensionScope', DimensionScopeQuerySet], _DimensionScopeManager):  # pyright: ignore
    """Model manager for DimensionScope."""
del _DimensionScopeManager


class DimensionScope(OrderedModel, PermissionedModel):
    """Link a dimension to a context in which it can be used, such as a plan or a category type."""

    dimension = models.ForeignKey(Dimension, on_delete=models.CASCADE, related_name='scopes')
    scope_content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, related_name='+')
    scope_id = models.PositiveIntegerField()
    scope = GenericForeignKey(
        'scope_content_type', 'scope_id',
    )
    identifier = models.CharField(
        blank=True,
        null=True,
        max_length=100,
        verbose_name=_('identifier'),
        help_text=_("Optional identifier that, if set, must be unique in the scope"),
    )

    objects: ClassVar[DimensionScopeManager] = DimensionScopeManager()
    _default_manager: ClassVar[DimensionScopeQuerySet]

    class Meta:
        verbose_name = _('dimension scope')
        verbose_name_plural = _('dimension scopes')
        constraints = (
            models.UniqueConstraint(
                fields=['identifier', 'scope_content_type', 'scope_id'],
                name='unique_identifier_per_dimension_scope',
            ),
        )

    def __str__(self):
        return f'{self.dimension.name} ({self.scope})'


class DatasetSchema(ClusterableModel, PermissionedModel):
    class TimeResolution(models.TextChoices):
        """
        Time resolution of all data points.

        If a dataset has monthly time resolution, then each data point applies to the entire month
        the data point's time belongs to. For yearly resolution, the data point applies to the entire
        year the date belongs to.
        """

        # TBD: Could also be separate model. (Some customers might be very creative in their granularities.)
        YEARLY = 'yearly', _('Yearly')
        # QUARTERLY = 'quarterly', _('Quarterly')
        # MONTHLY = 'monthly', _('Monthly')
        # WEEKLY = 'weekly', _('Weekly')
        # DAILY = 'daily', _('Daily')
        # HOURLY = 'hourly', _('Hourly')

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    time_resolution = models.CharField(
        max_length=16, choices=TimeResolution.choices,
        default=TimeResolution.YEARLY,
        help_text=_('Time resolution of the time stamps of data points in this dataset'),
    )
    name = models.CharField(max_length=100, blank=False, verbose_name=_('name'))
    description = models.TextField(blank=True)
    start_date = models.DateField(
        verbose_name=_('start date'),
        blank=True,
        null=True,
        help_text=("For a newly created dataset, start entering values from this year"),
    )

    i18n = TranslationField(fields=['name'])
    name_i18n: str

    objects: models.Manager[DatasetSchema]

    datasets: RevMany[Dataset]

    objects: ClassVar[DatasetSchemaQuerySet] = DatasetSchemaQuerySet.as_manager() # pyright: ignore
    _default_manager: ClassVar[DatasetSchemaQuerySet]

    panels = [
        FieldPanel(
            'name',
            heading=_("Name"),
            help_text=_("Descriptive name of the dataset schema"),
        ),
        FieldPanel(
            'description',
            heading=_("Description"),
            help_text=_("Description of the content and use of the dataset"),
        ),
        FieldPanel(
            'time_resolution',
            heading=_("Time resolution"),
        ),
        FieldPanel(
            'start_date',
            heading=_("Initial date"),
        ),
        InlinePanel(
            'metrics',
            heading=_("Metrics"),
            help_text=_("Defines the interpretation and units for the values of the dataset"),
            panels=[
                FieldPanel('label'),
                FieldPanel('unit')
            ]
        ),
        InlinePanel(
            'dimensions',
            heading=_("Dimensions"),
            help_text=_("Used when metrics are tracked for multiple categories"),
            panels=[
                FieldPanel('dimension'),
            ]
        ),
    ]

    class Meta:
        verbose_name = _('dataset schema')
        verbose_name_plural = _('dataset schemas')

    def __str__(self):
        if self.name_i18n:
            return f'{self.name_i18n}'
        return str(self.uuid)

    def __rich_repr__(self) -> RichReprResult:
        yield 'uuid', self.uuid
        yield 'time_resolution', self.time_resolution
        yield 'name', self.name
        yield 'start_date', self.start_date

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    @classmethod
    def permission_policy(cls) -> ModelPermissionPolicy[Self, QS[Self]]:
        return get_permission_policy('SCHEMA_PERMISSION_POLICY')

    @staticmethod
    def get_for_scope(scope_id: int, scope_content_type_id: int) -> list[DatasetSchema]:
        return list(
            DatasetSchema.objects.filter(
                scopes__scope_id=scope_id, scopes__scope_content_type__id=scope_content_type_id,
            ),
        )

    @staticmethod
    def get_for_model(obj: models.Model) -> list[DatasetSchema]:
        """Get schemas for any model that can have datasets."""
        content_type = ContentType.objects.get_for_model(obj)

        # For Action objects, look up schemas via their Plan
        if content_type.app_label == 'actions' and content_type.model == 'action':
            plan = getattr(obj, 'plan', None)
            if plan:
                plan_type = ContentType.objects.get_for_model(plan)
                return DatasetSchema.get_for_scope(plan.pk, plan_type.id)

        # For Category objects, look up schemas via their CategoryType
        elif content_type.app_label == 'actions' and content_type.model == 'category':
            category_type = getattr(obj, 'type', None)
            if category_type:
                type_content_type = ContentType.objects.get_for_model(category_type)
                return DatasetSchema.get_for_scope(category_type.pk, type_content_type.id)
        elif content_type.app_label == 'nodes' and content_type.model == 'instanceconfig':
            return DatasetSchema.get_for_scope(obj.pk, content_type.id)
        return []

    def delete(self, *args, **kwargs):
        retval = super().delete(*args, **kwargs)
        return retval


class DatasetMetric(OrderedModel, UUIDIdentifiedModel, PermissionedModel):
    schema = ParentalKey(DatasetSchema, on_delete=models.CASCADE, related_name='metrics', null=False, blank=False)
    name = models.CharField(verbose_name=_('name'), max_length=100, null=True, blank=True)
    """Maps to the DataFrame column name."""
    label = models.CharField(verbose_name=_('label'), max_length=100)
    unit = models.CharField(verbose_name=_('unit'), blank=True, max_length=50)

    i18n = TranslationField(fields=('label', 'unit'))

    objects: ClassVar[DatasetMetricQuerySet] = DatasetMetricQuerySet.as_manager() # pyright: ignore
    _default_manager: ClassVar[DatasetMetricQuerySet]

    def __str__(self):
        return self.label or self.name or str(self.uuid)

    def __rich_repr__(self) -> RichReprResult:
        yield 'schema', self.schema
        yield 'name', self.name

    def filter_siblings(self, qs: models.QuerySet[DatasetMetric]) -> models.QuerySet[DatasetMetric]:
        return qs.filter(schema=self.schema)


class DatasetSchemaDimension(OrderedModel, PermissionedModel):
    schema = ParentalKey(DatasetSchema, on_delete=models.CASCADE, related_name='dimensions', null=False, blank=False)
    dimension = models.ForeignKey(Dimension, on_delete=models.CASCADE, related_name='schemas', null=False, blank=False)

    objects: ClassVar[DatasetSchemaDimensionQuerySet] = DatasetSchemaDimensionQuerySet.as_manager() # pyright: ignore
    _default_manager: ClassVar[DatasetSchemaDimensionQuerySet]

    class Meta:
        verbose_name = _('dataset schema dimension')
        verbose_name_plural = _('dataset schema dimensions')

    def filter_siblings(self, qs: models.QuerySet[DatasetSchemaDimension]) -> models.QuerySet[DatasetSchemaDimension]:
        return qs.filter(schema=self.schema)


class DatasetQuerySet(PermissionedQuerySet['Dataset']):
    def for_instance_config(self, instance_config: InstanceConfig) -> Self:
        return self.filter(
            scope_content_type=ContentType.objects.get_for_model(instance_config),
            scope_id=instance_config.pk,
        )

    def for_plan(self, plan: Plan) -> Self:
        from actions.models import Plan  # type: ignore

        return self.filter(scope_content_type=ContentType.objects.get_for_model(Plan), scope_id=plan.pk)


_DatasetManager = models.Manager.from_queryset(DatasetQuerySet)
class DatasetManager(ModelManager['Dataset', DatasetQuerySet], _DatasetManager):  # pyright: ignore
    """Model manager for Dataset."""
del _DatasetManager


class Dataset(UserModifiableModel, UUIDIdentifiedModel, PermissionedModel):
    schema: FK[DatasetSchema | None] = models.ForeignKey(
        DatasetSchema, null=True, blank=True, related_name='datasets',
        verbose_name=_('schema'), on_delete=models.PROTECT,
    )
    identifier = models.CharField(
        blank=True,
        null=True,
        max_length=100,
        verbose_name=_('identifier'),
        help_text=_("Optional identifier that, if set, must be unique in the dataset's scope"),
    )

    # The "scope" generic foreign key links this dataset to an action or category
    # or instance
    scope_content_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE, related_name='+',
        null=True, blank=True,
    )
    scope_id = models.PositiveIntegerField(null=True, blank=True)
    scope = GenericForeignKey(
        'scope_content_type', 'scope_id',
    )

    objects: ClassVar[DatasetManager] = DatasetManager()
    mgr: ClassVar[DatasetManager] = DatasetManager()
    _default_manager: ClassVar[DatasetQuerySet]

    class Meta:  # pyright:ignore
        verbose_name = _('dataset')
        verbose_name_plural = _('datasets')
        ordering = ('id',)
        constraints = (
            models.UniqueConstraint(
                fields=['schema', 'scope_content_type', 'scope_id'],
                name='unique_dataset_per_scope_per_schema',
            ),
            models.UniqueConstraint(
                fields=['identifier', 'scope_content_type', 'scope_id'],
                name='unique_identifier_per_dataset_scope',
            ),
        )

    def __str__(self):
        if dataset_config.SCHEMA_HAS_SINGLE_DATASET:
            return str(self.schema)
        return f'Dataset {self.uuid}'

    def __rich_repr__(self) -> RichReprResult:
        yield 'schema', self.schema
        yield 'identifier', self.identifier
        yield 'scope', self.scope

    def save(self, *args, **kwargs):
        if self.schema is None:
            self.schema = DatasetSchema.objects.create()
        super().save(*args, **kwargs)

    @classmethod
    def permission_policy(cls) -> ModelPermissionPolicy[Self, QS[Self]]:
        return get_permission_policy('DATASET_PERMISSION_POLICY')

    def clear_scope_instance_cache(self):
        if self.scope_content_type is None:
            return
        if (self.scope_content_type.app_label == 'nodes' and
                self.scope_content_type.model == 'instanceconfig'):
            if self.scope is None:
                return
            ic = self.scope
            ic.invalidate_cache()


class DatasetSchemaScope(PermissionedModel):
    """Link a dataset schema to a context in which it can be used."""

    schema = models.ForeignKey(DatasetSchema, on_delete=models.CASCADE, related_name='scopes')
    scope_content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, related_name='+')
    scope_id = models.PositiveIntegerField()
    scope = GenericForeignKey(
        'scope_content_type', 'scope_id',
    )

    objects: ClassVar[DatasetSchemaScopeQuerySet] = DatasetSchemaScopeQuerySet.as_manager() # pyright: ignore
    _default_manager: ClassVar[DatasetSchemaScopeQuerySet]

    class Meta:
        verbose_name = _('dataset schema scope')
        verbose_name_plural = _('dataset schema scopes')

    def __str__(self):
        return f'DatasetSchemaScope schema:{self.schema.uuid} scope:{self.scope}'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        retval = super().delete(*args, **kwargs)
        return retval


# Note that the P in DataPoint is upper case. Rationale: The word "datapoint" seems to be rarely used.
# Source: https://english.stackexchange.com/questions/508238/word-choice-data-points-or-datapoints
# This is in contract to "dataset", which seems to be more common than "data set".
# Source: https://english.stackexchange.com/questions/2120/which-is-correct-dataset-or-data-set
class DataPoint(UserModifiableModel, UUIDIdentifiedModel, PermissionedModel):
    dataset = models.ForeignKey(
        Dataset, related_name='data_points', on_delete=models.CASCADE, verbose_name=_('dataset'),
    )
    dimension_categories = models.ManyToManyField(
        DimensionCategory, related_name='data_points', blank=True, verbose_name=_('dimension categories'),
    )
    date = models.DateField(
        verbose_name=_('date'),
        help_text=_("Date of this data point in context of the dataset's time resolution"),
    )

    metric = models.ForeignKey(
        DatasetMetric, related_name='data_points', on_delete=models.PROTECT, verbose_name=_('metric')
    )
    value = models.DecimalField(
        max_digits=32,
        decimal_places=16,
        verbose_name=_('value'),
        # null means that the data point is explicitly marked as not available or not applicable, for example
        # - category combination not applicable or
        # - data is known to be unavailable for date
        null=True,
        blank=True,
    )

    objects: ClassVar[DataPointQuerySet] = DataPointQuerySet.as_manager() # pyright: ignore
    _default_manager: ClassVar[DataPointQuerySet]

    class Meta:  # pyright:ignore
        verbose_name = _('data point')
        verbose_name_plural = _('data points')
        ordering = ('date',)

        # TODO: Enforce uniqueness constraint.
        # This doesn't work because dimension_categories is a many-to-many field.
        # constraints = [
        #     models.UniqueConstraint(fields=['dataset', 'dimension_categories', 'date'],
        #                             name='unique_data_point_value')
        # ]

    def __str__(self):
        return f'DataPoint {self.uuid} / dataset {self.dataset.uuid}'

    def __rich_repr__(self) -> RichReprResult:
        yield 'dataset', self.dataset
        yield 'date', self.date
        yield 'metric', self.metric
        yield 'value', self.value

    @classmethod
    def permission_policy(cls) -> ModelPermissionPolicy[Self, QS[Self]]:
        return get_permission_policy('DATA_POINT_PERMISSION_POLICY')


class DataPointComment(UserModifiableModel, PermissionedModel):
    class CommentType(models.TextChoices):
        REVIEW = 'review', _('Review comment')
        STICKY = 'sticky', _('Sticky comment')
        PLAIN = 'plain', _('Comment')

    class ReviewState(models.TextChoices):
        RESOLVED = 'resolved', _('Resolved')
        UNRESOLVED = 'unresolved', _('Unresolved')

    datapoint = models.ForeignKey(DataPoint, null=True, blank=True, on_delete=models.CASCADE, related_name='comments')
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    text = models.TextField()
    type = models.CharField(
        default=CommentType.PLAIN,
        max_length=20,
        choices=CommentType.choices,
    )
    review_state = models.CharField(
        blank=True,
        max_length=20,
        choices=ReviewState.choices,
    )
    resolved_at = models.DateTimeField(
        verbose_name=_('resolved at'), editable=False, null=True,
    )
    resolved_by: FK[User | None] = models.ForeignKey(
        'users.User', null=True, on_delete=models.SET_NULL, related_name='resolved_comments',
    )

    objects: ClassVar[DataPointCommentQuerySet] = DataPointCommentQuerySet.as_manager() # pyright: ignore
    _default_manager: ClassVar[DataPointCommentQuerySet]

    def __str__(self):
        return 'Comment on datapoint %s (created by %s at %s)' % (self.datapoint, self.created_by, self.created_at)

    class Meta:
        ordering = ('datapoint', '-created_at')
        verbose_name = _('comment')
        verbose_name_plural = _('comments')


class DataSource(UserModifiableModel, PermissionedModel):
    """
    Reference to some published data source.

    DataSource is used to track where specific data values in datasets have come from.
    Can be linked to any model that represents an "instance" context.
    """

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    # Generic foreign key to any instance model
    scope_content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, related_name='+')
    scope_id = models.PositiveIntegerField()
    scope = GenericForeignKey('scope_content_type', 'scope_id')

    name = models.CharField(max_length=200, null=False, blank=False, verbose_name=_('name'))
    edition = models.CharField(max_length=100, null=True, blank=True, verbose_name=_('edition'))
    authority = models.CharField(
        max_length=200,
        verbose_name=_('authority'),
        help_text=_('The organization responsible for the data source'),
        null=True,
        blank=True,
    )
    description = models.TextField(null=True, blank=True, verbose_name=_('description'))
    url = models.URLField(verbose_name=_('URL'), null=True, blank=True)

    objects: ClassVar[DataSourceQuerySet] = DataSourceQuerySet.as_manager() # pyright: ignore
    _default_manager: ClassVar[DataSourceQuerySet]

    def get_label(self):
        name, *rest = [p for p in (self.name, self.authority, self.edition) if p is not None]
        return f'{name}, {" ".join(rest)}'

    def __str__(self):
        return self.get_label()

    def __rich_repr__(self) -> RichReprResult:
        yield 'uuid', self.uuid
        yield 'scope', self.scope
        yield 'name', self.name

    class Meta:
        verbose_name = _('Data source')
        verbose_name_plural = _('Data sources')

    def natural_key(self):
        return (str(self.uuid),)


class DatasetSourceReference(UserModifiableModel, PermissionedModel):
    datapoint: FK[DataPoint | None] = models.ForeignKey(
        DataPoint, null=True, on_delete=models.CASCADE, related_name='source_references'
    )
    dataset: FK[Dataset | None] = models.ForeignKey(
        Dataset, null=True, on_delete=models.CASCADE, related_name='source_references'
    )
    data_source = models.ForeignKey(DataSource, on_delete=models.PROTECT, related_name='references')

    objects: ClassVar[DatasetSourceReferenceQuerySet] = DatasetSourceReferenceQuerySet.as_manager() # pyright: ignore
    _default_manager: ClassVar[DatasetSourceReferenceQuerySet]

    def __str__(self):
        dp = self.datapoint
        if dp:
            return f"Source reference for datapoint {dp.uuid} in dataset {dp.dataset.uuid}: {self.data_source}"
        ds = self.dataset
        if ds:
            return f"Source reference for dataset {ds.uuid}: {self.data_source}"
        return 'Source reference without datapoint or dataset'

    class Meta:
        ordering = ('datapoint__dataset', 'datapoint')
        verbose_name = _('data source reference')
        verbose_name_plural = _('data source references')
