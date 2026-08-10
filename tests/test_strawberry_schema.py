import asyncio
from typing import TYPE_CHECKING

from strawberry.extensions import SchemaExtension

import pytest

from kausal_common.strawberry.schema import ExceptionSafeExecutingContextManager

if TYPE_CHECKING:
    from collections.abc import Generator

pytestmark = pytest.mark.django_db


class HookSetupError(Exception):
    pass


class EnteredHook(SchemaExtension):
    def __init__(self, events: list[str]) -> None:
        super().__init__()
        self.events = events

    def on_execute(self) -> Generator[None]:
        self.events.append('enter first')
        try:
            yield
        except HookSetupError:
            self.events.append('first received failure')
            raise
        finally:
            self.events.append('exit first')


class FailingHook(SchemaExtension):
    def __init__(self, events: list[str]) -> None:
        super().__init__()
        self.events = events

    def on_execute(self) -> Generator[None]:
        self.events.append('enter failing')
        raise HookSetupError
        yield


def test_execution_hooks_unwind_when_sync_hook_setup_fails() -> None:
    events: list[str] = []
    manager = ExceptionSafeExecutingContextManager([EnteredHook(events), FailingHook(events)])

    with pytest.raises(HookSetupError), manager:
        pass

    assert events == ['enter first', 'enter failing', 'first received failure', 'exit first']


def test_execution_hooks_unwind_when_async_hook_setup_fails() -> None:
    events: list[str] = []
    manager = ExceptionSafeExecutingContextManager([EnteredHook(events), FailingHook(events)])

    async def execute() -> None:
        with pytest.raises(HookSetupError):
            async with manager:
                pass

    asyncio.run(execute())

    assert events == ['enter first', 'enter failing', 'first received failure', 'exit first']
