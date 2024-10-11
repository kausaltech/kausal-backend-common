from django.db import models

from _typeshed import Incomplete

class BaseViewRestriction(models.Model):
    NONE: str
    PASSWORD: str
    GROUPS: str
    LOGIN: str
    RESTRICTION_CHOICES: Incomplete
    restriction_type: Incomplete
    password: Incomplete
    groups: Incomplete
    def accept_request(self, request): ...
    def mark_as_passed(self, request) -> None:
        """
        Update the session data in the request to mark the user as having passed this
        view restriction
        """

    class Meta:
        abstract: bool
        verbose_name: Incomplete
        verbose_name_plural: Incomplete
