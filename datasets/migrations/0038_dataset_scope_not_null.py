import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Every dataset has a scope.

    Paths backfills its pre-2026-06 scopeless placeholders in a migration that runs
    before this one; Watch has never left the scope unset.
    """

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('datasets', '0037_source_reference_targets_exactly_one'),
    ]

    operations = [
        migrations.AlterField(
            model_name='dataset',
            name='scope_content_type',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to='contenttypes.contenttype'),
        ),
        migrations.AlterField(
            model_name='dataset',
            name='scope_id',
            field=models.PositiveIntegerField(),
        ),
    ]
