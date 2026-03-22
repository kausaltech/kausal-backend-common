from collections.abc import Callable, Generator
from datetime import datetime
from typing import Any, ClassVar, Self, TypedDict, Unpack
from uuid import UUID

from django.contrib.auth.models import AbstractUser
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.functional import cached_property as cached_property
from django_stubs_ext import StrOrPromise
from wagtail.log_actions import LogFormatter
from wagtail.models import Revision
from wagtail.users.utils import get_deleted_user_display_name as get_deleted_user_display_name

class LogEntryQuerySet[M: BaseLogEntry[Any] = BaseLogEntry[AbstractUser], UserModel: AbstractUser = AbstractUser](
    models.QuerySet[M, M]
):
    def get_actions(self) -> set[str]:
        """
        Returns a set of actions used by at least one log entry in this QuerySet
        """
    def get_user_ids(self) -> set[int]:
        """
        Returns a set of user IDs of users who have created at least one log entry in this QuerySet
        """
    def get_users(self) -> models.QuerySet[UserModel]:
        """
        Returns a QuerySet of Users who have created at least one log entry in this QuerySet.

        The returned queryset is ordered by the username.
        """
    def get_content_type_ids(self) -> set[int]:
        """
        Returns a set of IDs of content types with logged actions in this QuerySet
        """
    def filter_on_content_type(self, content_type: ContentType) -> Self: ...
    def with_instances(self) -> Generator[tuple[M, models.Model | None]]: ...

class LogActionArgs[UserModel: AbstractUser = AbstractUser](TypedDict, total=False):
    user: UserModel
    uuid: UUID
    title: str
    data: dict[str, Any]
    content_changed: bool
    deleted: bool
    timestamp: datetime

class BaseLogEntryManager[
    M: BaseLogEntry[Any] = BaseLogEntry[AbstractUser],
    QS: LogEntryQuerySet[Any, Any] = LogEntryQuerySet[M, AbstractUser],
    BaseModel: models.Model = models.Model,
    UserModel: AbstractUser = AbstractUser,
](models.Manager[M]):
    def get_queryset(self) -> QS: ...
    def get_instance_title(self, instance: BaseModel) -> str: ...
    def log_action(self, instance: BaseModel, action: str, **kwargs: Unpack[LogActionArgs[UserModel]]) -> M | None:
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
    def viewable_by_user(self, user: UserModel) -> QS: ...
    def get_for_model(self, model: type[BaseModel]) -> QS: ...
    def get_for_user(self, user_id: int) -> QS: ...
    def for_instance(self, instance: BaseModel) -> QS:
        """
        Return a queryset of log entries from this log model that relate to the given object instance
        """

class BaseLogEntry[UserModel: AbstractUser = AbstractUser](models.Model):
    content_type: models.ForeignKey[ContentType]
    label: models.TextField[str, str]
    action: models.CharField[str, str]
    data: models.JSONField
    timestamp: models.DateTimeField[datetime, datetime]
    uuid: models.UUIDField[UUID | None, UUID | None]
    user: models.ForeignKey[UserModel]
    revision: models.ForeignKey[Revision[Any] | None]
    content_changed: models.BooleanField[bool, bool]
    deleted: models.BooleanField[bool, bool]
    objects: ClassVar[BaseLogEntryManager[Any, Any, Any, Any]]
    wagtail_reference_index_ignore: bool

    def save(self, *args, **kwargs): ...
    def clean(self) -> None: ...
    @cached_property
    def user_display_name(self) -> StrOrPromise:
        """
        Returns the display name of the associated user;
        get_full_name if available and non-empty, otherwise get_username.
        Defaults to 'system' when none is provided
        """
    @cached_property
    def object_verbose_name(self) -> Callable[[], str]: ...
    @cached_property
    def formatter(self) -> LogFormatter: ...
    @cached_property
    def message(self) -> StrOrPromise: ...
    @cached_property
    def comment(self) -> str: ...

class ModelLogEntryManager[M: ModelLogEntry = ModelLogEntry](BaseLogEntryManager[M]):
    def log_action(self, instance, action, **kwargs): ...
    def for_instance(self, instance): ...

class ModelLogEntry(BaseLogEntry):
    """
    Simple logger for generic Django models
    """

    object_id: models.CharField[str, str]
    objects: ClassVar[ModelLogEntryManager[Any]]
