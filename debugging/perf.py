from __future__ import annotations

import enum
import inspect
import time
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, ClassVar

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
    "Identifier for the performance counter"

    show_time_to_last: bool = False
    "Flag to display time since last measurement"

    level: Level = Level.INFO
    "Logging level for this counter"

    shown_level: ClassVar[int] = Level.INFO.value
    "Global logging level threshold for all counters"

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
            pc.display("All done")
