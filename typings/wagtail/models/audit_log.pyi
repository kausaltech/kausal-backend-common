from _typeshed import Incomplete
from collections.abc import Generator
from django.db import models
from django.utils.functional import cached_property as cached_property
from wagtail.users.utils import get_deleted_user_display_name as get_deleted_user_display_name

class LogEntryQuerySet(models.QuerySet):
    def get_actions(self):
        """
        Returns a set of actions used by at least one log entry in this QuerySet
        """
    def get_user_ids(self):
        """
        Returns a set of user IDs of users who have created at least one log entry in this QuerySet
        """
    def get_users(self):
        """
        Returns a QuerySet of Users who have created at least one log entry in this QuerySet.

        The returned queryset is ordered by the username.
        """
    def get_content_type_ids(self):
        """
        Returns a set of IDs of content types with logged actions in this QuerySet
        """
    def filter_on_content_type(self, content_type): ...
    def with_instances(self) -> Generator[Incomplete, None, None]: ...

class BaseLogEntryManager(models.Manager):
    def get_queryset(self): ...
    def get_instance_title(self, instance): ...
    def log_action(self, instance, action, **kwargs):
        """
        :param instance: The model instance we are logging an action for
        :param action: The action. Should be namespaced to app (e.g. wagtail.create, wagtail.workflow.start)
        :param kwargs: Addition fields to for the model deriving from BaseLogEntry
            - user: The user performing the action
            - uuid: uuid shared between log entries from the same user action
            - title: the instance title
            - data: any additional metadata
            - content_changed, deleted - Boolean flags
        :return: The new log entry
        """
    def viewable_by_user(self, user): ...
    def get_for_model(self, model): ...
    def get_for_user(self, user_id): ...
    def for_instance(self, instance) -> None:
        """
        Return a queryset of log entries from this log model that relate to the given object instance
        """

class BaseLogEntry(models.Model):
    content_type: Incomplete
    label: Incomplete
    action: Incomplete
    data: Incomplete
    timestamp: Incomplete
    uuid: Incomplete
    user: Incomplete
    revision: Incomplete
    content_changed: Incomplete
    deleted: Incomplete
    objects: Incomplete
    wagtail_reference_index_ignore: bool
    class Meta:
        abstract: bool
        verbose_name: Incomplete
        verbose_name_plural: Incomplete
        ordering: Incomplete
    def save(self, *args, **kwargs): ...
    def clean(self) -> None: ...
    @cached_property
    def user_display_name(self):
        """
        Returns the display name of the associated user;
        get_full_name if available and non-empty, otherwise get_username.
        Defaults to 'system' when none is provided
        """
    @cached_property
    def object_verbose_name(self): ...
    def object_id(self) -> int: ...
    @cached_property
    def formatter(self): ...
    @cached_property
    def message(self): ...
    @cached_property
    def comment(self): ...

class ModelLogEntryManager(BaseLogEntryManager):
    def log_action(self, instance, action, **kwargs): ...
    def for_instance(self, instance): ...

class ModelLogEntry(BaseLogEntry):
    """
    Simple logger for generic Django models
    """
    object_id: Incomplete
    objects: Incomplete
    class Meta:
        ordering: Incomplete
        verbose_name: Incomplete
        verbose_name_plural: Incomplete
