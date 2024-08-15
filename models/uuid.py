from __future__ import annotations

import re

from django.contrib.postgres.functions import RandomUUID
from django.db import models
from django.utils.translation import gettext_lazy as _

UUID_PATTERN = re.compile(r'^[\da-f]{8}-([\da-f]{4}-){3}[\da-f]{12}$', re.IGNORECASE)


def is_uuid(s: str):
    return bool(UUID_PATTERN.match(s))


def is_valid_pk_or_uuid(s: str):
    if is_uuid(s):
        return True
    if s.isnumeric():
        return True
    return False


def query_pk_or_uuid(s: str):
    if is_uuid(s):
        return models.Q(uuid=s)
    else:
        return models.Q(id=int(s))


class UUIDIdentifiedModel(models.Model):
    uuid = models.UUIDField(_('UUID'), editable=False, db_default=RandomUUID(), unique=True)  # pyright: ignore

    class Meta:
        abstract = True
