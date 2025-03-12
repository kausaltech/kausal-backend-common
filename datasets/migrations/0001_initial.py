# Generated by Django 5.0.10 on 2025-02-24 13:46

import django.db.models.deletion
import modelcluster.fields
import modeltrans.fields
import uuid
from django.db import migrations, models


OLD_PATHS_TABLES = (
    'datasets_datasetdimensionselectedcategory',
    'datasets_datasetdimension',
    'datasets_datasetcomment',
    'datasets_datasetmetric',
    'datasets_datasetsourcereference',
    'datasets_dataset',
    'datasets_dimensioncategory',
    'datasets_dimension',
)


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [
        migrations.RunSQL([
            f"DROP TABLE IF EXISTS {table};"
            for table in OLD_PATHS_TABLES
        ]),
        migrations.CreateModel(
            name="DatasetSchema",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "uuid",
                    models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
                ),
                (
                    "time_resolution",
                    models.CharField(
                        choices=[("yearly", "Yearly")],
                        default="yearly",
                        help_text="Time resolution of the time stamps of data points in this dataset",
                        max_length=16,
                    ),
                ),
                (
                    "unit",
                    models.CharField(blank=True, max_length=100, verbose_name="unit"),
                ),
                ("name", models.CharField(max_length=100, verbose_name="name")),
                (
                    "start_date",
                    models.DateField(
                        blank=True,
                        help_text="First applicable date for datapoints in these datasets",
                        null=True,
                        verbose_name="start date",
                    ),
                ),
                (
                    "i18n",
                    modeltrans.fields.TranslationField(
                        fields=["unit", "name"],
                        required_languages=(),
                        virtual_fields=True,
                    ),
                ),
            ],
            options={
                "verbose_name": "dataset schema",
                "verbose_name_plural": "dataset schemas",
            },
        ),
        migrations.CreateModel(
            name="Dimension",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "uuid",
                    models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
                ),
                ("name", models.CharField(max_length=100, verbose_name="name")),
                (
                    "i18n",
                    modeltrans.fields.TranslationField(
                        fields=["name"], required_languages=(), virtual_fields=True
                    ),
                ),
            ],
            options={
                "verbose_name": "dimension",
                "verbose_name_plural": "dimensions",
                "ordering": ("name",),
            },
        ),
        migrations.CreateModel(
            name="Dataset",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "uuid",
                    models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
                ),
                ("scope_id", models.PositiveIntegerField(blank=True, null=True)),
                (
                    "scope_content_type",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="+",
                        to="contenttypes.contenttype",
                    ),
                ),
                (
                    "schema",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="datasets",
                        to="datasets.datasetschema",
                        verbose_name="schema",
                    ),
                ),
            ],
            options={
                "verbose_name": "dataset",
                "verbose_name_plural": "datasets",
                "ordering": ("id",),
            },
        ),
        migrations.CreateModel(
            name="DatasetSchemaScope",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("scope_id", models.PositiveIntegerField()),
                (
                    "schema",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="scopes",
                        to="datasets.datasetschema",
                    ),
                ),
                (
                    "scope_content_type",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="+",
                        to="contenttypes.contenttype",
                    ),
                ),
            ],
            options={
                "verbose_name": "dataset schema scope",
                "verbose_name_plural": "dataset schema scopes",
            },
        ),
        migrations.CreateModel(
            name="DimensionCategory",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("order", models.PositiveIntegerField(default=0, verbose_name="order")),
                (
                    "uuid",
                    models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
                ),
                ("label", models.CharField(max_length=100, verbose_name="label")),
                (
                    "i18n",
                    modeltrans.fields.TranslationField(
                        fields=["label"], required_languages=(), virtual_fields=True
                    ),
                ),
                (
                    "dimension",
                    modelcluster.fields.ParentalKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="categories",
                        to="datasets.dimension",
                    ),
                ),
            ],
            options={
                "verbose_name": "dimension category",
                "verbose_name_plural": "dimension categories",
            },
        ),
        migrations.CreateModel(
            name="DatasetSchemaDimensionCategory",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("order", models.PositiveIntegerField(default=0, verbose_name="order")),
                (
                    "schema",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="dimension_categories",
                        to="datasets.datasetschema",
                    ),
                ),
                (
                    "category",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="schemas",
                        to="datasets.dimensioncategory",
                    ),
                ),
            ],
            options={
                "verbose_name": "dataset schema dimension category",
                "verbose_name_plural": "dataset schema dimension categories",
            },
        ),
        migrations.CreateModel(
            name="DataPoint",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "uuid",
                    models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
                ),
                (
                    "date",
                    models.DateField(
                        help_text="Date of this data point in context of the dataset's time resolution",
                        verbose_name="date",
                    ),
                ),
                (
                    "value",
                    models.DecimalField(
                        blank=True,
                        decimal_places=4,
                        max_digits=10,
                        null=True,
                        verbose_name="value",
                    ),
                ),
                (
                    "dataset",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="data_points",
                        to="datasets.dataset",
                        verbose_name="dataset",
                    ),
                ),
                (
                    "dimension_categories",
                    models.ManyToManyField(
                        blank=True,
                        related_name="data_points",
                        to="datasets.dimensioncategory",
                        verbose_name="dimension categories",
                    ),
                ),
            ],
            options={
                "verbose_name": "data point",
                "verbose_name_plural": "data points",
                "ordering": ("date",),
            },
        ),
        migrations.CreateModel(
            name="DimensionScope",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("order", models.PositiveIntegerField(default=0, verbose_name="order")),
                ("scope_id", models.PositiveIntegerField()),
                (
                    "dimension",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="scopes",
                        to="datasets.dimension",
                    ),
                ),
                (
                    "scope_content_type",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="+",
                        to="contenttypes.contenttype",
                    ),
                ),
            ],
            options={
                "verbose_name": "dimension scope",
                "verbose_name_plural": "dimension scopes",
            },
        ),
        migrations.AddConstraint(
            model_name="dataset",
            constraint=models.UniqueConstraint(
                fields=("schema", "scope_content_type", "scope_id"),
                name="unique_dataset_per_scope_per_schema",
            ),
        ),
    ]
