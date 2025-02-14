# Generated by Django 5.0.6 on 2024-08-05 06:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('budget', '0004_alter_datasetschema_name'),
        ('contenttypes', '0002_remove_content_type_name'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='dataset',
            constraint=models.UniqueConstraint(fields=('schema', 'scope_content_type', 'scope_id'), name='unique_dataset_per_instance_per_schema'),
        ),
    ]
