import types
from collections.abc import Mapping
from typing import Iterable, Self
from uuid import UUID

from django.contrib.auth.base_user import AbstractBaseUser
from django.db.models import Model
from django.db.models.query import QuerySet
from wagtail import hooks as hooks
from wagtail.models.audit_log import BaseLogEntry
from wagtail.utils.registry import ObjectTypeRegistry as ObjectTypeRegistry

class LogFormatter:
    """
    Defines how to format log messages / comments for a particular action type. Messages that depend on
    log entry data should override format_message / format_comment; static messages can just be set as the
    'message' / 'comment' attribute.

    To be registered with log_registry.register_action.
    """
    label: str
    message: str
    comment: str
    def format_message(self, log_entry) -> str: ...
    def format_comment(self, log_entry) -> str: ...


class LogContext:
    """
    Stores data about the environment in which a logged action happens -
    e.g. the active user - to be stored in the log entry for that action.
    """
    user: AbstractBaseUser | None
    uuid: UUID | None
    def __init__(self, user: AbstractBaseUser | None = None, generate_uuid: bool = True) -> None: ...
    def __enter__(self) -> Self: ...
    def __exit__(
        self, type: type[BaseException] | None, value: BaseException | None, traceback: types.TracebackType | None
    ) -> None: ...

empty_log_context: LogContext

def activate(log_context: LogContext) -> None: ...
def deactivate() -> None: ...
def get_active_log_context() -> LogContext: ...

class LogActionRegistry:
    """
    A central store for log actions.
    The expected format for registered log actions: Namespaced action, Action label, Action message (or callable)
    """
    has_scanned_for_actions: bool
    formatters: Mapping[str, LogFormatter]
    choices: list[tuple[str, str]]
    log_entry_models_by_type: ObjectTypeRegistry
    log_entry_models: set[type[BaseLogEntry]]
    def __init__(self) -> None: ...
    def scan_for_actions(self) -> None: ...
    def register_model(self, cls: Model, log_entry_model: type[BaseLogEntry]) -> None: ...
    def register_action(self, action: str, *args): ...
    def get_choices(self) -> list[tuple[str, str]]: ...
    def get_formatter(self, log_entry: BaseLogEntry) -> LogFormatter: ...
    def action_exists(self, action: str) -> bool: ...
    def get_log_entry_models(self) -> Iterable[type[BaseLogEntry]]: ...
    def get_action_label(self, action: str) -> str: ...
    def get_log_model_for_model(self, model: Model) -> type[BaseLogEntry]: ...
    def get_log_model_for_instance(self, instance: Model) -> type[BaseLogEntry]: ...
    def log(
        self, instance: Model, action: str, user: AbstractBaseUser | None = None, uuid: UUID | None = None, **kwargs
    ) -> BaseLogEntry: ...
    def get_logs_for_instance(self, instance: Model) -> QuerySet[BaseLogEntry]: ...

registry: LogActionRegistry

def log(instance: Model, action: str, **kwargs) -> BaseLogEntry: ...
