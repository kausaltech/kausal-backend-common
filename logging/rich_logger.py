from __future__ import annotations

import functools
import logging
from collections.abc import Callable, Generator, Sequence
from contextlib import contextmanager
from datetime import datetime
from logging import LogRecord
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import loguru
from rich.console import Console, ConsoleRenderable, RenderableType
from rich.containers import Renderables
from rich.logging import RichHandler
from rich.style import Style
from rich.text import Text, TextType

from kausal_common.deployment import env_bool
from kausal_common.logging.handler import loguru_make_record

if TYPE_CHECKING:
    from rich.traceback import Traceback

FormatTimeCallable = Callable[[datetime], Text]

log_console: Console | None = None


class LogRender:
    def __init__(
        self,
        show_time: bool = True,
        show_level: bool = False,
        show_path: bool = True,
        time_format: str | FormatTimeCallable = '[%x %X]',
        omit_repeated_times: bool = True,
        level_width: int | None = 8,
    ) -> None:
        self.show_time = show_time
        self.show_level = show_level
        self.show_path = show_path
        self.time_format = time_format
        self.omit_repeated_times = omit_repeated_times
        self.level_width = level_width
        self._last_time: Text | None = None

    def __call__(  # noqa: C901, PLR0912
        self,
        console: Console,
        renderables: Sequence[ConsoleRenderable],
        name: str,
        log_time: datetime | None = None,
        time_format: str | FormatTimeCallable | None = None,
        level: TextType = '',
        path: str | None = None,
        line_no: int | None = None,
        link_path: str | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> Renderables:
        from rich.table import Table

        output = Table.grid(padding=(0, 1))
        output.expand = True
        if self.show_time:
            output.add_column(style='log.time')
        if self.show_level:
            output.add_column(style='log.level', width=self.level_width)
        output.add_column(ratio=1, style='log.message', overflow='fold')
        if self.show_path and path:
            output.add_column(style='log.path')
        row: list[RenderableType] = []
        if self.show_time:
            log_time = log_time or console.get_datetime()
            time_format = time_format or self.time_format
            if callable(time_format):
                log_time_display = time_format(log_time)
            else:
                log_time_display = Text(log_time.strftime(time_format))
            if log_time_display == self._last_time and self.omit_repeated_times:
                row.append(Text(' ' * len(log_time_display)))
            else:
                row.append(log_time_display)
                self._last_time = log_time_display
        if self.show_level:
            row.append(level)

        if attributes:
            attr_text = Text()
            for key, val in attributes.items():
                text = Text.assemble((str(key), 'log.path'), '=', (str(val), 'log.value'), ' ')
                attr_text.append(text)
            attr_renderables = [attr_text]
        else:
            attr_renderables = []

        if len(renderables) == 1 and isinstance(renderables[0], Text) and '\n' not in renderables[0].plain:
            row.append(Renderables([*renderables, *attr_renderables]))
            renderables = []
        else:
            row.append('')

        if self.show_path and path:
            path_text = Text()
            path_text.append(
                name,
                style=f'link file://{link_path}#{line_no}' if link_path else '',
            )
            row.append(path_text)

        output.add_row(*row)

        combined_renderables: list[ConsoleRenderable] = [output]
        combined_renderables.extend(renderables)
        return Renderables(combined_renderables)


RICH_TIME_FORMAT = '%H:%M:%S.%f'


def get_rich_log_console() -> Console:
    global log_console  # noqa: PLW0603

    if log_console is None:
        log_console = Console(stderr=True)
    return log_console


class RichLogHandler(RichHandler):
    _log_render: LogRender  # type: ignore[assignment]

    def __init__(self):
        super().__init__(
            log_time_format=RICH_TIME_FORMAT,
            console=get_rich_log_console(),
            rich_tracebacks=True,
            tracebacks_show_locals=env_bool('TRACEBACK_SHOW_LOCALS', default=False),
        )
        lr = self._log_render
        self._log_render = LogRender(
            show_time=lr.show_time,
            show_level=lr.show_level,
            show_path=lr.show_path,
            time_format=RICH_TIME_FORMAT,
            omit_repeated_times=lr.omit_repeated_times,
            level_width=None,
        )
        self.formatter = logging.Formatter(fmt='%(message)s')

    def format(self, record: LogRecord) -> str:
        return super().format(record)

    def add_extra(self, msg: Text, record: LogRecord):
        extra = {}
        if hasattr(record, '_extra_keys'):
            extra_keys = getattr(record, '_extra_keys', None)
            if extra_keys:
                extra = {key: getattr(record, key) for key in extra_keys if hasattr(record, key)}
            delattr(record, '_extra_keys')

        scope_parts: list[Text] = []

        correlation_id = extra.pop('correlation_id', None)
        if correlation_id:
            scope_parts.append(
                Text.assemble(
                    '[',
                    Text.styled(correlation_id, Style(color=identifier_color(correlation_id), underline=True)),
                    ']',
                )
            )

        trace_id = extra.pop('trace.id', None)
        if trace_id:
            sampled = extra.pop('trace.sampled', None)
            scope_parts.append(
                Text.assemble(
                    '[Trace ',
                    Text.styled(trace_id, Style(color=identifier_color(trace_id), underline=True)),
                    ' (sampled: ',
                    Text.styled(sampled, Style(color='green' if sampled else 'red')),
                    ')]',
                )
            )

        def add_scope(style: str, key: str) -> None:
            if key not in extra:
                return
            val = extra.pop(key)
            text = Text.assemble((key, 'log.path'), '=', (val, style))
            scope_parts.append(text)

        add_scope('scope.key', 'tenant')
        add_scope('scope.key', 'instance')
        add_scope('inspect.attr.dunder', 'instance_obj_id')
        add_scope('inspect.attr.dunder', 'context')
        add_scope('json.key', 'session')
        other_extra = {key: value for key, value in extra.items() if key not in ('markup',)}  # noqa: FURB171
        if scope_parts:
            out = Text()
            record.highlighter = None
            for part in scope_parts:
                out.append_text(part)
                out.append(' ')
            out.append_text(msg)
            msg = out
        record._attributes = other_extra
        return msg

    def render_message(self, record: LogRecord, message: str) -> ConsoleRenderable:
        if getattr(record, 'markup', False):
            record.highlighter = None
        ret = super().render_message(record, message)
        if isinstance(ret, Text):
            ret = self.add_extra(ret, record)
        return ret

    def render(
        self,
        *,
        record: LogRecord,
        traceback: Traceback | None,
        message_renderable: ConsoleRenderable,
    ) -> ConsoleRenderable:
        """
        Render log for display.

        Args:
        ----
            record (LogRecord): logging Record.
            traceback (Optional[Traceback]): Traceback instance or None for no Traceback.
            message_renderable (ConsoleRenderable): Renderable (typically Text) containing log message contents.

        Returns:
        -------
            ConsoleRenderable: Renderable to display log.

        """
        path = Path(record.pathname).name
        level = self.get_level_text(record)
        time_format = None if self.formatter is None else self.formatter.datefmt
        log_time = datetime.fromtimestamp(record.created)  # noqa: DTZ006

        log_renderable = self._log_render(
            self.console,
            [message_renderable] if not traceback else [message_renderable, traceback],
            name=record.name,
            log_time=log_time,
            time_format=time_format,
            level=level,
            path=path,
            line_no=record.lineno,
            link_path=record.pathname if self.enable_link_path else None,
            attributes=getattr(record, '_attributes', {}),
        )

        return log_renderable


rich_handler = RichLogHandler()


def loguru_rich_sink(message: loguru.Message):
    rec = loguru_make_record(message.record)
    rich_handler.acquire()
    try:
        rich_handler.emit(rec)
    finally:
        rich_handler.release()


daphne_logger = loguru.logger.bind(name='daphne.request', markup=True)


def styled_http_method(method: str) -> str:
    match method:
        case 'GET':
            method_style = 'yellow'
        case 'OPTIONS':
            method_style = 'dim yellow'
        case 'POST':
            method_style = 'orange4'
        case 'PUT':
            method_style = 'orange4'
        case 'DELETE':
            method_style = 'red'
        case _:
            method_style = 'white'
    return f'[{method_style}]{method}[/]'


def _daphne_log_action(self, protocol: str, action: str, details: dict[str, Any]) -> None:  # noqa: C901, PLR0912, PLR0915  # pyright: ignore[reportUnusedParameter]
    # HTTP requests
    if protocol == 'http' and action == 'complete':
        log_level: str = 'INFO'
        status_style: str
        status = details['status']
        # Utilize terminal colors, if available
        if 200 <= status < 300:
            # Put 2XX first, since it should be the common case
            status_style = 'green'
        elif 100 <= status < 200:
            status_style = 'bold white'
        elif status == 304:
            status_style = 'dim cyan'
        elif 300 <= status < 400:
            status_style = 'yellow'
        elif status == 404:
            status_style = 'dim red'
            log_level = 'WARNING'
        elif 400 <= status < 500:
            status_style = 'red'
            log_level = 'WARNING'
        else:
            # Any 5XX, or any other response
            status_style = 'white on red'
            log_level = 'ERROR'

        time_taken = details['time_taken']
        if time_taken < 0.01:
            time_taken_style = 'blue'
        elif time_taken < 0.1:
            time_taken_style = 'bright_blue'
        elif time_taken < 0.5:
            time_taken_style = 'yellow'
        elif time_taken < 1:
            time_taken_style = 'bold yellow'
        else:
            time_taken_style = 'red'

        size = details['size']
        if size < 10 * 1024:
            size_style = 'dim yellow'
        elif size < 100 * 1024:
            size_style = 'orange4'
        elif size < 400 * 1024:
            size_style = 'red'
        else:
            size_style = 'white on red'

        method = details['method']

        msg = (
            'HTTP response: %(styled_method)s {path} [%(status_style)s]{status}[/] '
            '[[%(time_taken_style)s]{time_taken:.3f}s[/], [%(size_style)s]{size}[/] bytes, [dim yellow]{client}[/]]'
        ) % dict(
            styled_method=styled_http_method(method),
            status_style=status_style,
            time_taken_style=time_taken_style,
            size_style=size_style,
        )
        daphne_logger.log(log_level, msg.format(**details))

    # Websocket requests
    if protocol != 'websocket':
        return

    match action:
        case 'connected':
            ws_verb = 'CONNECT'
        case 'disconnected':
            ws_verb = 'DISCONNECT'
        case 'connecting':
            ws_verb = 'HANDSHAKING'
        case 'rejected':
            ws_verb = 'REJECT'
        case _:
            ws_verb = action
    daphne_logger.info('WebSocket [yellow]{ws_verb}[/] {path} [dim yellow]{client}[/]', ws_verb=ws_verb, **details)


IDENTIFIER_COLORS = [
    '#42952e',
    '#d6061a',
    '#26cdca',
    '#a44e74',
    '#8de990',
    '#c551dc',
    '#acf82f',
    '#4067be',
    '#dfb8f5',
    '#33837f',
    '#c8e6ff',
    '#e01e82',
    '#20f53d',
    '#b24b29',
    '#fbe423',
    '#937056',
    '#e1e995',
    '#fa1bfc',
    '#f8ba7c',
    '#ff8889',
]


def identifier_color(identifier: str) -> str:
    val = 0
    for char in identifier:
        val = (val << 5) - val + ord(char)
        val |= 0
    return IDENTIFIER_COLORS[val % len(IDENTIFIER_COLORS)]


def patch_daphne_runserver() -> None:
    from daphne.management.commands.runserver import Command  # type: ignore

    Command.log_action = _daphne_log_action


@contextmanager
def log_sql_queries() -> Generator[None]:
    """Log all SQL queries during the context."""

    from logging import getLogger

    logger = getLogger('django.db')
    current_level = logger.level
    try:
        logger.setLevel(logging.DEBUG)
        yield
    finally:
        logger.setLevel(current_level)


def enable_sql_query_logging[C: Callable[..., Any]](func: C) -> C:
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        with log_sql_queries():
            return func(*args, **kwargs)
    return cast('C', wrapper)
