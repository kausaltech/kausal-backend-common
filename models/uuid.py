from django.db import models
from django.utils.translation import gettext_lazy as _
from uuid import uuid4


class UUIDIdentifiedModel(models.Model):
    uuid = models.UUIDField(_('UUID'), editable=False, default=uuid4, unique=True)  # pyright: ignore

    class Meta:
        abstract = True
