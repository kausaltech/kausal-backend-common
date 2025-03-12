from __future__ import annotations

from django.db.models.signals import post_delete
from django.dispatch import receiver

from .config import dataset_config
from .models import Dataset


@receiver(post_delete, sender=Dataset)
def delete_one_to_one_schema(sender, instance, **kwargs):
    if dataset_config.SCHEMA_HAS_SINGLE_DATASET:
        instance.schema.delete()
