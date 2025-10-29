from __future__ import annotations

from django.apps import AppConfig


class DatasetsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'kausal_common.datasets'
    label = 'datasets'

    def ready(self):
        from wagtail.models import ReferenceIndex  # noqa: I001
        from .models import DataSource, DatasetSourceReference

        ReferenceIndex.register_model(DataSource)
        ReferenceIndex.register_model(DatasetSourceReference)
