from django.db import models
from uuid import uuid4


class UUIDIdentifiedModel(models.Model):
    uuid = models.UUIDField(editable=False, default=uuid4, unique=True)  # pyright: ignore

    class Meta:
        abstract = True
