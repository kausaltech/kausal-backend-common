from typing import Any

from celery.app.task import Task as Task

class DjangoTask(Task):
    """
    Extend the base :class:`~celery.app.task.Task` for Django.

    Provide a nicer API to trigger tasks at the end of the DB transaction.
    """
    def delay_on_commit(self, *args: Any, **kwargs: Any):
        """Call :meth:`~celery.app.task.Task.delay` with Django's ``on_commit()``."""

    def apply_async_on_commit(self, *args: Any, **kwargs: Any):
        """Call :meth:`~celery.app.task.Task.apply_async` with Django's ``on_commit()``."""
