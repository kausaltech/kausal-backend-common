from django.db import migrations


def drop_index_entries(apps, _schema_editor):
    """
    Delete the reference-index rows of the two models that are no longer indexed.

    Nothing maintains them any more: Wagtail removes an object's rows on delete only while
    its model is registered, so left behind they would go on naming references that no
    longer exist -- including as usages of the datasets they point at.
    """
    ContentType = apps.get_model('contenttypes', 'ContentType')
    ReferenceIndex = apps.get_model('wagtailcore', 'ReferenceIndex')
    content_types = ContentType.objects.filter(app_label='datasets', model__in=['datasource', 'datasetsourcereference'])
    ReferenceIndex.objects.filter(base_content_type__in=content_types).delete()


class Migration(migrations.Migration):
    """
    Stop indexing data sources and their references in Wagtail's reference index.

    No StreamField can hold either model, so the index only copied the
    ``DatasetSourceReference.data_source`` foreign key, which the admin now reads directly.
    """

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('datasets', '0038_dataset_scope_not_null'),
        ('wagtailcore', '0078_referenceindex'),
    ]

    operations = [
        migrations.RunPython(drop_index_entries, migrations.RunPython.noop),
    ]
