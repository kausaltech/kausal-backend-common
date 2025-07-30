from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import models
from django.utils.translation import gettext_lazy as _

if TYPE_CHECKING:
    from kausal_common.models.types import FK

    from users.models import User


class UserModifiableModel(models.Model):
    """
    An abstract base model that includes fields for tracking creation and modification.

    This model provides common fields for tracking when an object was created,
    who created it, when it was last modified, and who last modified it.
    It is designed to be inherited by other models that require this functionality.

    Fields:
        modified_at (DateTimeField): The timestamp of the last modification.
        created_at (DateTimeField): The timestamp of when the object was created.
        created_by (ForeignKey): The user who created the object.
        last_modified_by (ForeignKey): The user who last modified the object.
    """

    created_at = models.DateTimeField(verbose_name=_("Created at"), auto_now_add=True, editable=False)
    created_by: FK[User | None] = models.ForeignKey(
        'users.User',
        verbose_name=_("Last modified by"),
        on_delete=models.SET_NULL,
        null=True,
        editable=False,
        related_name='+',
    )
    last_modified_at = models.DateTimeField(verbose_name=_("Last modified at"), auto_now=True, editable=False)
    last_modified_by: FK[User | None] = models.ForeignKey(
        'users.User',
        verbose_name=_("Last modified by"),
        on_delete=models.SET_NULL,
        null=True,
        editable=False,
        related_name='+',
    )

    class Meta:
        abstract = True
