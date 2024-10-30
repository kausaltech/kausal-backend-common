from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from django.contrib.postgres.functions import RandomUUID
from django.db import models
from django.db.models import Q
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


def query_pk_or_uuid(s: str) -> Q:
    if is_uuid(s):
        return Q(uuid=s)
    return Q(id=int(s))


def query_pk_or_uuid_or_identifier(s: str) -> Q:
    if is_uuid(s):
        return Q(uuid=s)
    q = Q(identifier=s)
    if s.isnumeric():
        q |= Q(id=s)
    return q


class UUIDIdentifiedModel(models.Model):  # noqa: DJ008
    uuid = models.UUIDField(_('UUID'), editable=False, db_default=RandomUUID(), unique=True)  # pyright: ignore

    if TYPE_CHECKING:
        Meta: Any
    else:
        class Meta:
            abstract = True
