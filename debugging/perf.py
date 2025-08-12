from __future__ import annotations

from collections import defaultdict
import enum
import inspect
import sys
import sysconfig
import time
from contextlib import AbstractContextManager, contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
import traceback
from types import TracebackType
from typing import TYPE_CHECKING, Any, ClassVar, Self

from django.db.models.base import Model

if TYPE_CHECKING:
    from collections.abc import Generator


class PerfCounterContext:
    depth = 0


_pc_context = ContextVar[PerfCounterContext]('PerfCounterContext', default=PerfCounterContext())


@dataclass
class PerfCounter:
    """
    A performance counter class for measuring and displaying execution time.

    This class provides functionality to measure and display execution time
    of code blocks. It can be used to track performance at different levels
    of granularity and supports nested measurements.
    """

    class Level(enum.Enum):
        INFO = 0
        DEBUG = 1
        VERBOSE_DEBUG = 2

    label: str | None = None
    'Identifier for the performance counter'

    show_time_to_last: bool = False
    'Flag to display time since last measurement'

    level: Level = Level.INFO
    'Logging level for this counter'

    shown_level: ClassVar[int] = Level.INFO.value
    'Global logging level threshold for all counters'

    _start_time: int = field(init=False)
    _last_time: int = field(init=False)
    _display_counter: int = field(init=False)
    _is_displayed: bool = field(init=False)
    _is_finished: bool = field(init=False)

    @classmethod
    def change_level(cls, level: Level) -> None:
        cls.shown_level = level.value

    def __post_init__(self):
        self._display_counter = 0
        if self.label is None:
            # If no tag given, default to the name of the calling func
            frame = inspect.currentframe()
            assert frame is not None
            calling_frame = frame.f_back
            assert calling_frame is not None
            self.label = calling_frame.f_code.co_name

        if self.level.value <= self.shown_level:
            ctx = _pc_context.get()
            ctx.depth += 1
            self._is_displayed = True
        else:
            self._is_displayed = False

        self._is_finished = False
        self._start_time = time.perf_counter_ns()
        self._last_time = self._start_time

    def __del__(self):
        if not self._is_displayed or self._is_finished:
            return
        self.finish()

    def _update(self) -> tuple[int, float, float]:
        now = time.perf_counter_ns()
        diff_to_last = self._diff_to_ms(self._last_time)
        diff_to_start = self._diff_to_ms(self._start_time)
        self._last_time = now
        return (now, diff_to_start, diff_to_last)

    def finish(self) -> float:
        """
        Finish the performance counter and return the final measurement.

        Returns:
            float: The total elapsed time in milliseconds since the counter started.

        This method finalizes the performance counter, displays the total elapsed time,
        and updates the context depth. It should be called when the measured operation
        is complete. If the counter's level is higher than the shown level, no output
        is displayed.

        """

        diff = self._diff_to_ms(self._start_time)
        if not self._is_displayed:
            return diff
        self._is_finished = True

        ctx = _pc_context.get()
        ctx.depth -= 1
        assert ctx.depth >= 0
        return diff

    def _diff_to_ms(self, to: int, now: int | None = None) -> float:
        if now is None:
            now = time.perf_counter_ns()
        return (now - to) / 1000000

    def measure(self) -> float:
        """
        Measure the elapsed time since the last measurement.

        Returns:
            float: The elapsed time in milliseconds since the last measurement.

        This method updates the internal 'last_value' attribute with the current time
        and returns the time difference in milliseconds. It's useful for measuring
        the duration of specific operations within the overall timing context.

        """
        assert not self._is_finished

        (_, diff_to_start, diff_to_last) = self._update()
        return diff_to_start if self.show_time_to_last else diff_to_last

    def display(self, name: str | None = None, show_time_to_last: bool = False):
        """
        Display the elapsed time since the counter started or since the last measurement.

        Args:
            name: Optional name for this measurement. If None, a counter is used.
            show_time_to_last: If True, shows time elapsed since last measurement.

        Returns:
            float: The elapsed time in milliseconds since the last measurement, if show_time_to_last is True.
                   Otherwise, returns the elapsed time since the counter started.

        This method prints the elapsed time in milliseconds, along with the counter's tag
        and the provided name or counter number. If show_time_to_last is True or set during
        initialization, it also displays the time elapsed since the last measurement.

        The output is indented based on the current depth of nested counters.

        """
        assert not self._is_finished

        (_, diff_to_start_ms, diff_to_last_ms) = self._update()
        show_time_to_last = show_time_to_last or self.show_time_to_last

        ret = diff_to_last_ms if show_time_to_last else diff_to_start_ms

        if not self._is_displayed:
            return ret

        if not name:
            name = '%d' % self._display_counter
            self._display_counter += 1

        tag_str = '[%s] ' % self.label if self.label else ''
        if show_time_to_last:
            diff_str = ' (to previous %4.1f ms)' % (diff_to_last_ms)
        else:
            diff_str = ''
        ctx = _pc_context.get()
        print('%s%s%6.1f ms%s: %s' % ((ctx.depth - 1) * '  ', tag_str, diff_to_start_ms, diff_str, name))
        if show_time_to_last:
            return diff_to_last_ms
        return ret

    @classmethod
    @contextmanager
    def time_it(cls, label: str | None = None, level: Level = Level.INFO) -> Generator[PerfCounter, Any, None]:
        """
        Create a context for timing code execution.

        This method creates a PerfCounter instance with the given tag and yields it.
        The counter is automatically started when entering the context and stopped
        when exiting.

        Args:
            label: An optional label to identify the timing context.
            level: Logging level for this counter

        Yields:
            PerfCounter: An instance of PerfCounter for measuring execution time.

        Example:
            with PerfCounter.time_it("example_operation") as pc:
                # Code to be timed
                pc.display("operation 1 done")
                # ... more code
                pc.display("operation 2 done")
                time_in_ms = pc.finish()

        """
        pc = cls(label=label, level=level)
        yield pc
        if not pc._is_finished:
            pc.display('All done')



STDLIB_PATH = sysconfig.get_path('stdlib')
PLATLIB_PATH = sysconfig.get_path('platlib')

@dataclass(slots=True)
class ModelCreationFrameCount:
    stack: traceback.StackSummary | None = None
    gql_path: tuple[str, ...] | None = None
    count: int = 1

    def __str__(self):
        from django.conf import settings
        if self.stack is None:
            assert self.gql_path is not None
            return f'GraphQL path: {'.'.join(self.gql_path)} ({self.count})'
        last_frame = self.stack[-1]
        filename = last_frame.filename.removeprefix(settings.BASE_DIR)
        return f'{filename}:{last_frame.lineno} ({self.count})'

@dataclass(slots=True)
class ModelCreation:
    count: int = 0
    by_stack_trace: dict[int, ModelCreationFrameCount] = field(default_factory=dict, init=False)
    unknown_count: int = 0

    def mark(self):
        self.count += 1

        frame = sys._getframe().f_back.f_back.f_back  # type: ignore[union-attr]
        list_value_frame = None
        while frame := frame.f_back:  # type: ignore[union-attr]
            if frame.f_code.co_name == 'complete_list_value':
                list_value_frame = frame
            if frame.f_code.co_filename.startswith(STDLIB_PATH):
                continue
            if frame.f_code.co_filename.startswith(PLATLIB_PATH):
                continue
            if frame.f_code.co_name == '__init__':
                continue
            break

        if frame is None:
            if list_value_frame is not None:
                info = list_value_frame.f_locals['info']
                info_path = tuple(info.path.as_list())
                path_hash = hash(info_path)
                by_stack = self.by_stack_trace.get(path_hash)
                if by_stack is None:
                    self.by_stack_trace[path_hash] = ModelCreationFrameCount(stack=None, gql_path=info_path)
                else:
                    by_stack.count += 1
                return

            print("Unknown frame:\n%s" % '\n'.join(traceback.format_stack(limit=20)))
            self.unknown_count += 1
            return

        code_hash = hash(frame.f_code)
        by_stack = self.by_stack_trace.get(code_hash)
        if by_stack is None:
            ss = traceback.extract_stack(frame, limit=3)
            self.by_stack_trace[code_hash] = ModelCreationFrameCount(ss)
        else:
            by_stack.count += 1


@dataclass
class ModelCreationCounter(AbstractContextManager):
    """
    Track model instance creation counts.

    This is useful to debug performance issues by finding out which models are
    instanciated the most. Used as a context manager to ensure that the Django
    signal receivers are disconnected when the context is exited.

    Note: It doesn't track model saving in the database, but only what gets
    instanciated in the Python process through e.g. queries.
    """

    creation_per_model: dict[str, ModelCreation] = field(default_factory=dict, init=False)

    def __enter__(self) -> Self:
        from django.db.models.signals import post_init

        self.creation_per_model = dict()
        post_init.connect(self.model_post_init)
        return self

    def __exit__(self, exc_type: type[BaseException] | None, exc_value: BaseException | None, traceback: TracebackType | None, /):
        from django.db.models.signals import post_init

        post_init.disconnect(self.model_post_init)
        self.display()

    def model_post_init(self, /, sender: type[Model], instance: Any, **kwargs):
        name = f'{sender.__module__}.{sender.__name__}'
        per_model = self.creation_per_model.get(name)
        if per_model is None:
            per_model = ModelCreation()
            self.creation_per_model[name] = per_model
        per_model.mark()

    def display(self):
        sorted_items = sorted(self.creation_per_model.items(), key=lambda x: x[1].count, reverse=True)
        for name, per_model in sorted_items:
            print(f'{name}: {per_model.count}')
            if per_model.count < 10:
                continue
            if per_model.unknown_count > 0:
                print('  %d unknown creations' % per_model.unknown_count)
            for _, frame_count in sorted(per_model.by_stack_trace.items(), key=lambda x: x[1].count, reverse=True):
                print('  %d creations' % frame_count.count)
                if frame_count.stack is not None:
                    printed_stack = frame_count.stack.format()
                    print('\n'.join(['    %s' % f for f in printed_stack]))
                else:
                    print('    %s' % frame_count)

