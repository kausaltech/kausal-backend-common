from __future__ import annotations

import contextlib
import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Protocol, Self

from rich import box
from rich.console import Console
from rich.table import Table
from rich.text import Text

from kausal_common.const import IS_WATCH

if TYPE_CHECKING:
    from collections.abc import Callable, Generator
    from types import TracebackType

DEBUG = False

type PerfAttrValue = str | int | float | bool | None
type PerfAttrs = dict[str, PerfAttrValue]


def estimate_size_bytes(obj: object) -> int | None:
    from polars import DataFrame as PolarsDataFrame

    if isinstance(obj, PolarsDataFrame):
        try:
            size = obj.estimated_size()
        except TypeError:
            return None
        return int(size)

    if not IS_WATCH:
        from pandas import DataFrame as PandasDataFrame

        if isinstance(obj, PandasDataFrame):
            try:
                usage = obj.memory_usage(deep=True)
            except TypeError:
                return None
            total = usage.sum()
            return int(total)

    if hasattr(obj, '__sizeof__'):
        return int(obj.__sizeof__())

    return None


@dataclass
class PerfStats:
    nr_calls: int = 0
    exec_time: float = 0
    cum_exec_time: float = 0
    cache_hits: int = 0
    cache_misses: int = 0


class HasId(Protocol):
    id: str


class PerfKind(StrEnum):
    NODE = 'node'
    DATASET = 'dataset'
    DATASET_REPO = 'dataset_repo'
    GRAPHQL = 'graphql'
    CACHE = 'cache'
    FUNCTION = 'function'


class PerfSubject(Protocol):
    @property
    def kind(self) -> str: ...

    @property
    def id(self) -> str: ...

    @property
    def op(self) -> str: ...


@dataclass(frozen=True, slots=True)
class PerfSubjectRef:
    kind: str
    id: str
    op: str

    @property
    def full_name(self) -> str:
        return f'{self.kind}.{self.op}'


@dataclass(slots=True)
class PerfSpanSummary:
    kind: str
    op: str
    count: int = 0
    total_exclusive_duration_ns: int = 0
    max_exclusive_duration_ns: int = 0

    @property
    def avg_exclusive_duration_ns(self) -> float:
        if self.count == 0:
            return 0.0
        return self.total_exclusive_duration_ns / self.count

    @property
    def full_name(self) -> str:
        return f'{self.kind}.{self.op}'

    def add(self, entry: PerfSpanEntry[Any, Any]) -> None:
        duration_ns = entry.exclusive_duration_ns
        self.count += 1
        self.total_exclusive_duration_ns += duration_ns
        self.max_exclusive_duration_ns = max(self.max_exclusive_duration_ns, duration_ns)


@dataclass(slots=True)
class PerfNodeClassSummary:
    class_name: str
    count: int = 0
    total_local_duration_ns: int = 0
    max_local_duration_ns: int = 0

    @property
    def avg_local_duration_ns(self) -> float:
        if self.count == 0:
            return 0.0
        return self.total_local_duration_ns / self.count

    def add(self, duration_ns: int) -> None:
        self.count += 1
        self.total_local_duration_ns += duration_ns
        self.max_local_duration_ns = max(self.max_local_duration_ns, duration_ns)


@dataclass(slots=True)
class PerfNodeClassOpSummary:
    class_name: str
    kind: str
    op: str
    count: int = 0
    total_duration_ns: int = 0
    max_duration_ns: int = 0

    @property
    def avg_duration_ns(self) -> float:
        if self.count == 0:
            return 0.0
        return self.total_duration_ns / self.count

    def add(self, entry: PerfSpanEntry[Any, Any]) -> None:
        duration_ns = entry.exclusive_duration_ns
        self.count += 1
        self.total_duration_ns += duration_ns
        self.max_duration_ns = max(self.max_duration_ns, duration_ns)


@dataclass(slots=True)
class PerfSpanEntry[ObjType: Any, CacheResultType: Any = Any]:
    run: PerfRunContext[ObjType, CacheResultType]
    subject: PerfSubjectRef
    obj: ObjType | None
    parent: Self | None
    children: list[Self] = field(init=False, default_factory=list)
    started_at: int = field(init=False)
    finished_at: int = field(init=False, default=0)
    cache_res: CacheResultType | None = field(init=False, default=None)
    depth: int = field(init=False)
    attrs: PerfAttrs = field(init=False, default_factory=dict)

    def __post_init__(self):
        self.started_at = self.now()
        self.depth = 0 if self.parent is None else self.parent.depth + 1
        self.debug('create  %s' % self.time_ms(self.started_at))

    def now(self) -> int:
        return self.run.now()

    def time_ms(self, value: int) -> str:
        return '%.3f ms' % (value / 1000000.0)

    if DEBUG:

        def debug(self, msg: str) -> None:
            print('%-5s: %s%s [%s]: %s' % (self.time_ms(self.now()), '  ' * self.depth, self.subject.id, self.subject.op, msg))

    else:

        def debug(self, msg: str) -> None:
            pass

    @property
    def duration_ns(self) -> int:
        return self.finished_at - self.started_at

    @property
    def child_duration_ns(self) -> int:
        return sum(child.duration_ns for child in self.children)

    @property
    def exclusive_duration_ns(self) -> int:
        return max(0, self.duration_ns - self.child_duration_ns)

    def set_attr(self, key: str, value: PerfAttrValue | None) -> None:
        if value is None:
            return
        self.attrs[key] = value

    def set_attrs(self, attrs: PerfAttrs) -> None:
        for key, value in attrs.items():
            self.set_attr(key, value)

    def mark_cache(self, cache_res: CacheResultType) -> None:
        assert self.cache_res is None
        self.cache_res = cache_res

    @staticmethod
    def _format_bytes(value: int) -> str:
        units = ['B', 'KiB', 'MiB', 'GiB']
        nr = float(value)
        for unit in units:
            if nr < 1024 or unit == units[-1]:
                if unit == 'B':
                    return f'{int(nr)} {unit}'
                return f'{nr:.1f} {unit}'
            nr /= 1024
        return f'{nr:.1f} GiB'

    def format_attrs(self) -> str:
        if not self.attrs:
            return ''

        parts: list[str] = []
        for key in sorted(self.attrs):
            value = self.attrs[key]
            if key.endswith(('.bytes', '_bytes')) and isinstance(value, int):
                rendered = self._format_bytes(value)
            else:
                rendered = str(value)
            parts.append(f'{key}={rendered}')

        return ', '.join(parts)

    def display_label(self) -> str:
        if self.subject.kind == PerfKind.NODE and self.subject.op == 'compute':
            return self.subject.id
        return f'-> {self.subject.full_name}'


@dataclass(slots=True)
class PerfRunContext[ObjType: HasId, CacheResultType: Any = Any]:
    ctx: PerfContext[ObjType, CacheResultType]
    roots: list[PerfSpanEntry[ObjType, CacheResultType]] = field(init=False, default_factory=list)
    tip: PerfSpanEntry[ObjType, CacheResultType] | None = field(init=False, default=None)
    started_at: int = field(init=False, default_factory=time.perf_counter_ns)
    ended_at: int = field(init=False, default=0)

    def now(self) -> int:
        return time.perf_counter_ns() - self.started_at

    def enter(
        self,
        subject: PerfSubject,
        *,
        obj: ObjType | None = None,
        attrs: PerfAttrs | None = None,
    ) -> PerfSpanEntry[ObjType, CacheResultType]:
        entry = PerfSpanEntry(
            run=self,
            subject=PerfSubjectRef(kind=str(subject.kind), id=subject.id, op=subject.op),
            obj=obj,
            parent=self.tip,
        )
        if attrs:
            entry.set_attrs(attrs)
        if self.tip is None:
            self.roots.append(entry)
        else:
            self.tip.children.append(entry)
        self.tip = entry
        return entry

    def leave(self) -> None:
        cur = self.tip
        assert cur is not None
        cur.finished_at = self.now()
        cur.debug(
            'leave at %s (total %s, own %s)'
            % (
                cur.time_ms(cur.finished_at),
                cur.time_ms(cur.duration_ns),
                cur.time_ms(cur.exclusive_duration_ns),
            )
        )
        if cur.parent is None:
            assert cur == self.roots[-1]
        self.tip = cur.parent

    def iter_entries(self) -> Generator[PerfSpanEntry[ObjType, CacheResultType]]:
        for root in self.roots:
            yield from self._iter_entries(root)

    def _iter_entries(
        self,
        entry: PerfSpanEntry[ObjType, CacheResultType],
    ) -> Generator[PerfSpanEntry[ObjType, CacheResultType]]:
        yield entry
        for child in entry.children:
            yield from self._iter_entries(child)

    def summarize_spans(
        self,
        *,
        include: Callable[[PerfSpanEntry[ObjType, CacheResultType]], bool] | None = None,
    ) -> list[PerfSpanSummary]:
        summaries: dict[tuple[str, str], PerfSpanSummary] = {}
        for entry in self.iter_entries():
            if include is not None and not include(entry):
                continue
            key = (entry.subject.kind, entry.subject.op)
            summary = summaries.get(key)
            if summary is None:
                summary = summaries[key] = PerfSpanSummary(kind=entry.subject.kind, op=entry.subject.op)
            summary.add(entry)
        return sorted(summaries.values(), key=lambda item: (-item.total_exclusive_duration_ns, item.full_name))

    def summarize_non_compute_spans(self) -> list[PerfSpanSummary]:
        return self.summarize_spans(include=lambda entry: entry.subject.op != 'compute')

    @staticmethod
    def _is_node_compute_span(entry: PerfSpanEntry[ObjType, CacheResultType]) -> bool:
        return entry.subject.kind == PerfKind.NODE and entry.subject.op == 'compute'

    def _iter_local_entries(
        self,
        entry: PerfSpanEntry[ObjType, CacheResultType],
    ) -> Generator[PerfSpanEntry[ObjType, CacheResultType]]:
        yield entry
        for child in entry.children:
            if self._is_node_compute_span(child):
                continue
            yield from self._iter_local_entries(child)

    def summarize_node_classes(self) -> list[PerfNodeClassSummary]:
        summaries: dict[str, PerfNodeClassSummary] = {}
        for entry in self.iter_entries():
            if not self._is_node_compute_span(entry) or entry.obj is None:
                continue
            class_name = type(entry.obj).__name__
            local_duration_ns = sum(local_entry.exclusive_duration_ns for local_entry in self._iter_local_entries(entry))
            summary = summaries.get(class_name)
            if summary is None:
                summary = summaries[class_name] = PerfNodeClassSummary(class_name=class_name)
            summary.add(local_duration_ns)
        return sorted(summaries.values(), key=lambda item: (-item.total_local_duration_ns, item.class_name))

    def summarize_node_class_operation_mix(self) -> list[PerfNodeClassOpSummary]:
        summaries: dict[tuple[str, str, str], PerfNodeClassOpSummary] = {}
        for entry in self.iter_entries():
            if not self._is_node_compute_span(entry) or entry.obj is None:
                continue
            class_name = type(entry.obj).__name__
            for local_entry in self._iter_local_entries(entry):
                key = (class_name, local_entry.subject.kind, local_entry.subject.op)
                summary = summaries.get(key)
                if summary is None:
                    summary = summaries[key] = PerfNodeClassOpSummary(
                        class_name=class_name,
                        kind=local_entry.subject.kind,
                        op=local_entry.subject.op,
                    )
                summary.add(local_entry)
        return sorted(summaries.values(), key=lambda item: (-item.total_duration_ns, item.class_name, item.kind, item.op))

    def _run_duration_ns(self) -> int:
        if self.ended_at:
            return self.ended_at
        return self.now()

    def _total_exec_time_ms(self) -> float:
        return sum(root.duration_ns for root in self.roots) / 1000000.0

    def _dump_span_summary(self, table: Table) -> None:
        for summary in self.summarize_non_compute_spans():
            total_ms = summary.total_exclusive_duration_ns / 1000000.0
            if total_ms < self.ctx.min_ms:
                continue
            avg_ms = summary.avg_exclusive_duration_ns / 1000000.0
            max_ms = summary.max_exclusive_duration_ns / 1000000.0
            run_duration_ns = self._run_duration_ns()
            share = 0.0 if run_duration_ns <= 0 else (summary.total_exclusive_duration_ns / run_duration_ns) * 100
            table.add_row(
                summary.kind,
                summary.op,
                str(summary.count),
                f'{total_ms:.2f}',
                f'{avg_ms:.2f}',
                f'{max_ms:.2f}',
                f'{share:.1f}%',
            )

    def _dump_node_class_summary(self, table: Table) -> None:
        for summary in self.summarize_node_classes():
            total_ms = summary.total_local_duration_ns / 1000000.0
            if total_ms < self.ctx.min_ms:
                continue
            avg_ms = summary.avg_local_duration_ns / 1000000.0
            max_ms = summary.max_local_duration_ns / 1000000.0
            run_duration_ns = self._run_duration_ns()
            share = 0.0 if run_duration_ns <= 0 else (summary.total_local_duration_ns / run_duration_ns) * 100
            table.add_row(
                summary.class_name,
                str(summary.count),
                f'{total_ms:.2f}',
                f'{avg_ms:.2f}',
                f'{max_ms:.2f}',
                f'{share:.1f}%',
            )

    def _dump_node_class_operation_mix(self, table: Table) -> None:
        for summary in self.summarize_node_class_operation_mix():
            total_ms = summary.total_duration_ns / 1000000.0
            if total_ms < self.ctx.min_ms:
                continue
            avg_ms = summary.avg_duration_ns / 1000000.0
            max_ms = summary.max_duration_ns / 1000000.0
            run_duration_ns = self._run_duration_ns()
            share = 0.0 if run_duration_ns <= 0 else (summary.total_duration_ns / run_duration_ns) * 100
            table.add_row(
                summary.class_name,
                summary.kind,
                summary.op,
                str(summary.count),
                f'{total_ms:.2f}',
                f'{avg_ms:.2f}',
                f'{max_ms:.2f}',
                f'{share:.1f}%',
            )

    def _dump_recurse(self, siblings: list[PerfSpanEntry[ObjType, CacheResultType]], depth: int, table: Table) -> None:
        for entry in siblings:
            total_exec = entry.duration_ns / 1000000.0
            own_exec = entry.exclusive_duration_ns / 1000000.0
            if total_exec < self.ctx.min_ms:
                continue

            if self.ctx.supports_cache:
                cache_res = entry.cache_res
                if cache_res is None:
                    cache_text = Text('')
                else:
                    cache_text = Text('HIT' if cache_res.is_hit else 'MISS', style=cache_res.color)
                cache_cols = [
                    Text(cache_res.kind.name, style=cache_res.kind.color) if cache_res else Text('disabled', style='grey42'),
                    cache_text,
                ]
            else:
                cache_cols = []

            def format_num(num: float) -> Text:
                return Text('%.2f' % num, style='italic')

            label = '%s%s' % ('  ' * depth, entry.display_label())
            attrs = entry.format_attrs()
            if attrs:
                label = f'{label} ({attrs})'

            table.add_row(
                label,
                Text('  ' * depth) + format_num(total_exec),
                format_num(own_exec),
                *cache_cols,
            )
            self._dump_recurse(entry.children, depth + 1, table)

    @staticmethod
    def _print_if_has_rows(console: Console, table: Table) -> None:
        if table.row_count > 0:
            console.print(table)

    def _print_operation_breakdown(self, console: Console) -> None:
        span_summaries = self.summarize_non_compute_spans()
        if not span_summaries:
            return

        summary_table = Table(box=box.SIMPLE, row_styles=['on gray3', 'on gray7'], title='Operation Breakdown')
        summary_table.add_column('Kind', justify='left')
        summary_table.add_column('Operation', justify='left')
        summary_table.add_column('Count', justify='right')
        summary_table.add_column('Own total (ms)', justify='right')
        summary_table.add_column('Own avg (ms)', justify='right')
        summary_table.add_column('Own max (ms)', justify='right')
        summary_table.add_column('Run share', justify='right')
        self._dump_span_summary(summary_table)
        self._print_if_has_rows(console, summary_table)

    def _print_node_class_local_breakdown(self, console: Console) -> None:
        class_summaries = self.summarize_node_classes()
        if not class_summaries:
            return

        class_table = Table(box=box.SIMPLE, row_styles=['on gray3', 'on gray7'], title='Node Class Local Breakdown')
        class_table.add_column('Node class', justify='left')
        class_table.add_column('Count', justify='right')
        class_table.add_column('Local total (ms)', justify='right')
        class_table.add_column('Local avg (ms)', justify='right')
        class_table.add_column('Local max (ms)', justify='right')
        class_table.add_column('Run share', justify='right')
        self._dump_node_class_summary(class_table)
        self._print_if_has_rows(console, class_table)

    def _print_node_class_operation_mix(self, console: Console) -> None:
        op_mix_summaries = self.summarize_node_class_operation_mix()
        if not op_mix_summaries:
            return

        op_mix_table = Table(box=box.SIMPLE, row_styles=['on gray3', 'on gray7'], title='Node Class Operation Mix')
        op_mix_table.add_column('Node class', justify='left')
        op_mix_table.add_column('Kind', justify='left')
        op_mix_table.add_column('Operation', justify='left')
        op_mix_table.add_column('Count', justify='right')
        op_mix_table.add_column('Own total (ms)', justify='right')
        op_mix_table.add_column('Own avg (ms)', justify='right')
        op_mix_table.add_column('Own max (ms)', justify='right')
        op_mix_table.add_column('Run share', justify='right')
        self._dump_node_class_operation_mix(op_mix_table)
        self._print_if_has_rows(console, op_mix_table)

    def end(self, failed: bool) -> None:
        self.ended_at = self.now()
        if not self.roots:
            return

        console = Console()

        table = Table(box=box.SIMPLE, row_styles=['on gray3', 'on gray7'], title=self.ctx.description)
        table.add_column('Span', justify='left')
        table.add_column('Cum. time (ms)')
        table.add_column('Own time (ms)')
        if self.ctx.supports_cache:
            table.add_column('Cache')
            table.add_column('Cache kind')
        self._dump_recurse(self.roots, 0, table)
        console.print(table)
        print(f'Total exec time: {self._total_exec_time_ms():.2f} ms')
        self._print_operation_breakdown(console)
        self._print_node_class_local_breakdown(console)
        self._print_node_class_operation_mix(console)


class PerfContext[ObjType: HasId, CacheResultType: Any = Any](
    contextlib.AbstractContextManager[PerfRunContext[ObjType, CacheResultType]]
):
    run: PerfRunContext[ObjType, CacheResultType] | None
    enabled: bool = False
    min_ms: float
    description: str | None

    def __init__(self, supports_cache: bool, min_ms: float = 0.0, description: str | None = None):
        self.supports_cache = supports_cache
        self.min_ms = float(min_ms)
        self.description = description
        self.run = None

    def __enter__(self) -> PerfRunContext[ObjType, CacheResultType]:
        super().__enter__()
        run_ctx = PerfRunContext(self)
        if self.run is not None:
            raise RuntimeError('PerfContext already has a run active')
        self.run = run_ctx
        return run_ctx

    def __exit__(
        self, __exc_type: type[BaseException] | None, __exc_value: BaseException | None, __traceback: TracebackType | None, /
    ) -> bool | None:
        run = self.run
        if run is None:
            raise Exception('Exiting context with no previous run active')
        run.end(__exc_type is not None)
        self.run = None
        return None

    @staticmethod
    def make_subject(kind: str, id: str, op: str) -> PerfSubjectRef:
        return PerfSubjectRef(kind=kind, id=id, op=op)

    @contextlib.contextmanager
    def exec_span(
        self,
        subject: PerfSubject,
        *,
        obj: ObjType | None = None,
        attrs: PerfAttrs | None = None,
    ) -> Generator[PerfSpanEntry[ObjType, CacheResultType] | None]:
        if not self.enabled:
            yield None
            return

        run = self.run
        if run is None:
            yield None
            return

        entry = run.enter(subject, obj=obj, attrs=attrs)
        try:
            yield entry
        finally:
            run.leave()

    @contextlib.contextmanager
    def exec_node(
        self,
        node: ObjType,
        *,
        op: str = 'compute',
        attrs: PerfAttrs | None = None,
    ) -> Generator[PerfSpanEntry[ObjType, CacheResultType] | None]:
        subject = self.make_subject(kind=PerfKind.NODE, id=node.id, op=op)
        with self.exec_span(subject, obj=node, attrs=attrs) as entry:
            yield entry

    @contextlib.contextmanager
    def exec_named(
        self,
        *,
        kind: str,
        id: str,
        op: str,
        obj: ObjType | None = None,
        attrs: PerfAttrs | None = None,
    ) -> Generator[PerfSpanEntry[ObjType, CacheResultType] | None]:
        subject = self.make_subject(kind=kind, id=id, op=op)
        with self.exec_span(subject, obj=obj, attrs=attrs) as entry:
            yield entry

    def record_cache(self, node: ObjType, is_hit: bool) -> None:
        if not self.enabled:
            return

        return
