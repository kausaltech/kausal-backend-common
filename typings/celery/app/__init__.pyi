from _typeshed import Incomplete

from ..contrib.django import DjangoTask
from .base import Celery as Celery
from .utils import AppPickler as AppPickler

__all__ = ['Celery', 'AppPickler', 'shared_task']

default_app: Incomplete

def shared_task(*args, **kwargs) -> DjangoTask: ...
