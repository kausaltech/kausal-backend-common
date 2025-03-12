from __future__ import annotations

import uuid
from functools import lru_cache
from typing import TYPE_CHECKING, ClassVar, Self

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models.query import QuerySet
from django.utils.translation import gettext_lazy as _
from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel
from modeltrans.fields import TranslationField
from wagtail.admin.panels.field_panel import FieldPanel
from wagtail.admin.panels.inline_panel import InlinePanel

from kausal_common.models.fields import IdentifierField
from kausal_common.models.uuid import UUIDIdentifiedModel

from ..models.modification_tracking import UserModifiableModel
from ..models.ordered import OrderedModel
from ..models.types import ModelManager, RevMany
from .config import dataset_config

if TYPE_CHECKING:
    import contextlib

    from users.models import User

    from ..models.types import FK, RevMany
    with contextlib.suppress(ImportError):
        from actions.models import Plan  # type: ignore

        from nodes.models import InstanceConfig  # type: ignore


class Dimension(ClusterableModel, UUIDIdentifiedModel, UserModifiableModel):
    name = models.CharField(max_length=100, verbose_name=_('name'))

    i18n = TranslationField(fields=['name'])
    name_i18n: str

    scopes: RevMany[DimensionScope]

    class Meta:
        verbose_name = _('dimension')
        verbose_name_plural = _('dimensions')
        ordering = ('name',)

    def __str__(self):
        return self.name_i18n


class DimensionCategory(OrderedModel, UUIDIdentifiedModel, UserModifiableModel):
    identifier = IdentifierField[str | None, str | None](
        null=True, blank=True, help_text=_("Optional identifier that, if set, must be unique within the dimension"),
    )
    dimension = ParentalKey(Dimension, blank=False, on_delete=models.CASCADE, related_name='categories')
    label = models.CharField(max_length=100, verbose_name=_('label'))

    i18n = TranslationField(fields=['label'])
    label_i18n: str

    class Meta:
        verbose_name = _('dimension category')
        verbose_name_plural = _('dimension categories')
        constraints = (
            models.UniqueConstraint(
                fields=['identifier', 'dimension'],
                name='unique_identifier_per_dimension',
            ),
        )

    def __str__(self):
        if self.label:
            return f'{self.label_i18n} ({self.uuid})'
        return str(self.uuid)

    def filter_siblings(self, qs: models.QuerySet[DimensionCategory]) -> models.QuerySet[DimensionCategory]:
        return qs.filter(dimension=self.dimension)


class DimensionScopeQuerySet(QuerySet['DimensionScope']):
    def for_instance_config(self, instance_config: InstanceConfig) -> Self:
        return self.filter(scope_content_type=ContentType.objects.get_for_model(instance_config), scope_id=instance_config.pk)


_DimensionScopeManager = models.Manager.from_queryset(DimensionScopeQuerySet)
class DimensionScopeManager(ModelManager['DimensionScope', DimensionScopeQuerySet], _DimensionScopeManager):  # pyright: ignore
    """Model manager for DimensionScope."""
del _DimensionScopeManager


class DimensionScope(OrderedModel):
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

    class Meta:
        verbose_name = _('dimension scope')
        verbose_name_plural = _('dimension scopes')
        constraints = (
            models.UniqueConstraint(
                fields=['identifier', 'scope_content_type', 'scope_id'],
                name='unique_identifier_per_dimension_scope',
            ),
        )


class DatasetSchema(ClusterableModel):
    class TimeResolution(models.TextChoices):
        """
        Time resolution of all data points.

        If a dataset has, e.g., monthly time resolution, then each data point applies to the entire month in which
        the data point's time is.
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
    unit = models.CharField(max_length=100, blank=True, verbose_name=_('unit'))
    name = models.CharField(max_length=100, blank=False, verbose_name=_('name'))
    start_date = models.DateField(
        verbose_name=_('start date'),
        blank=True,
        null=True,
        help_text=_("First applicable date for datapoints in these datasets"),
    )

    i18n = TranslationField(fields=['unit', 'name'])
    unit_i18n: str
    name_i18n: str

    objects: models.Manager[DatasetSchema]

    datasets: RevMany[Dataset]

    panels = [
        FieldPanel(
            'name',
            heading=_("Name"),
            help_text=_("Descriptive name of the dataset schema"),
        ),
        FieldPanel(
            'unit',
            heading=_("Unit"),
            help_text=_("Unit of the dataset schema"),
        ),
        FieldPanel(
            'time_resolution',
            heading=_("Time Resolution"),
        ),
        FieldPanel(
            'start_date',
            heading=_("Start Date"),
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

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        DatasetSchema.get_for_scope.cache_clear()

    @staticmethod
    @lru_cache
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
        DatasetSchema.get_for_scope.cache_clear()
        return retval


class DatasetMetric(OrderedModel, UUIDIdentifiedModel):
    schema = ParentalKey(DatasetSchema, on_delete=models.CASCADE, related_name='metrics', null=False, blank=False)
    name = models.CharField(verbose_name=_('name'), max_length=100, null=True, blank=True)
    """Maps to the DataFrame column name."""
    label = models.CharField(verbose_name=_('label'), max_length=100)
    unit = models.CharField(verbose_name=_('unit'), blank=True, max_length=50)

    i18n = TranslationField(fields=('label', 'unit'))

    def __str__(self):
        return self.label or self.name or str(self.uuid)

    def filter_siblings(self, qs: models.QuerySet[DatasetMetric]) -> models.QuerySet[DatasetMetric]:
        return qs.filter(schema=self.schema)


class DatasetSchemaDimension(OrderedModel):
    schema = ParentalKey(DatasetSchema, on_delete=models.CASCADE, related_name='dimensions', null=False, blank=False)
    dimension = models.ForeignKey(Dimension, on_delete=models.CASCADE, related_name='schemas', null=False, blank=False)

    class Meta:
        verbose_name = _('dataset schema dimension')
        verbose_name_plural = _('dataset schema dimensions')

    def filter_siblings(self, qs: models.QuerySet[DatasetSchemaDimension]) -> models.QuerySet[DatasetSchemaDimension]:
        return qs.filter(schema=self.schema)


class DatasetQuerySet(QuerySet['Dataset']):
    def for_instance_config(self, instance_config: InstanceConfig) -> Self:
        return self.filter(scope_id=instance_config.pk)

    def for_plan(self, plan: Plan) -> Self:
        from actions.models import Plan  # type: ignore

        return self.filter(scope_content_type=ContentType.objects.get_for_model(Plan), scope_id=plan.pk)


_DatasetManager = models.Manager.from_queryset(DatasetQuerySet)
class DatasetManager(ModelManager['Dataset', DatasetQuerySet], _DatasetManager):  # pyright: ignore
    """Model manager for Dataset."""
del _DatasetManager


class Dataset(UserModifiableModel, UUIDIdentifiedModel):
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

    def save(self, *args, **kwargs):
        if self.schema is None:
            self.schema = DatasetSchema.objects.create()
        super().save(*args, **kwargs)


class DatasetSchemaScope(models.Model):
    """Link a dataset schema to a context in which it can be used."""

    schema = models.ForeignKey(DatasetSchema, on_delete=models.CASCADE, related_name='scopes')
    scope_content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, related_name='+')
    scope_id = models.PositiveIntegerField()
    scope = GenericForeignKey(
        'scope_content_type', 'scope_id',
    )

    class Meta:
        verbose_name = _('dataset schema scope')
        verbose_name_plural = _('dataset schema scopes')

    def __str__(self):
        return f'DatasetSchemaScope schema:{self.schema.uuid} scope:{self.scope}'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        DatasetSchema.get_for_scope.cache_clear()

    def delete(self, *args, **kwargs):
        retval = super().delete(*args, **kwargs)
        DatasetSchema.get_for_scope.cache_clear()
        return retval


class DataPoint(UserModifiableModel, UUIDIdentifiedModel):
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
        return f'Datapoint {self.uuid} / dataset {self.dataset.uuid}'


class DataPointComment(UserModifiableModel):
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

    def __str__(self):
        return 'Comment on datapoint %s (created by %s at %s)' % (self.datapoint, self.created_by, self.created_at)

    class Meta:
        ordering = ('datapoint', '-created_at')
        verbose_name = _('comment')
        verbose_name_plural = _('comments')


class DataSource(UserModifiableModel):
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

    def get_label(self):
        name, *rest = [p for p in (self.name, self.authority, self.edition) if p is not None]
        return f'{name}, {" ".join(rest)}'

    def __str__(self):
        return self.get_label()

    class Meta:
        verbose_name = _('Data source')
        verbose_name_plural = _('Data sources')

    def natural_key(self):
        return (str(self.uuid),)


class DatasetSourceReference(UserModifiableModel):
    datapoint: FK[DataPoint | None] = models.ForeignKey(
        DataPoint, null=True, on_delete=models.CASCADE, related_name='source_references'
    )
    dataset: FK[Dataset | None] = models.ForeignKey(
        Dataset, null=True, on_delete=models.CASCADE, related_name='source_references'
    )
    data_source = models.ForeignKey(DataSource, on_delete=models.PROTECT, related_name='references')

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
