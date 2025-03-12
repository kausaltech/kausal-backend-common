from __future__ import annotations

from django.apps import AppConfig


class DatasetsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'kausal_common.datasets'
    label = 'datasets'

    def ready(self):
        import kausal_common.datasets.signals  # noqa: F401
