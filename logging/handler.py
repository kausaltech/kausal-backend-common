from __future__ import annotations

import logging
import sys
import traceback
import warnings
from datetime import UTC, datetime
from logging import LogRecord, StreamHandler
from pathlib import Path
from typing import TYPE_CHECKING, Callable, List, Optional, Sequence, Type, Union, cast

import loguru
from logfmter.formatter import Logfmter
from loguru import logger
from rich.console import Console
from rich.containers import Renderables
from rich.logging import RichHandler
from rich.text import Text, TextType

from kausal_common.deployment import env_bool

if TYPE_CHECKING:
    from rich.console import ConsoleRenderable, RenderableType
    from rich.traceback import Traceback

FormatTimeCallable = Callable[[datetime], Text]


class LogRender:
    def __init__(
        self,
        show_time: bool = True,
        show_level: bool = False,
        show_path: bool = True,
        time_format: str | FormatTimeCallable = "[%x %X]",
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

    def __call__(
        self,
        console: Console,
        renderables: Sequence[ConsoleRenderable],
        name: str,
        log_time: datetime | None = None,
        time_format: str | FormatTimeCallable | None = None,
        level: TextType = "",
        path: str | None = None,
        line_no: int | None = None,
        link_path: str | None = None,
    ) -> Renderables:
        from rich.table import Table

        output = Table.grid(padding=(0, 1))
        output.expand = True
        if self.show_time:
            output.add_column(style="log.time")
        if self.show_level:
            output.add_column(style="log.level", width=self.level_width)
        output.add_column(ratio=1, style="log.message", overflow="fold")
        if self.show_path and path:
            output.add_column(style="log.path")
        row: list[RenderableType] = []
        if self.show_time:
            log_time = log_time or console.get_datetime()
            time_format = time_format or self.time_format
            if callable(time_format):
                log_time_display = time_format(log_time)
            else:
                log_time_display = Text(log_time.strftime(time_format))
            if log_time_display == self._last_time and self.omit_repeated_times:
                row.append(Text(" " * len(log_time_display)))
            else:
                row.append(log_time_display)
                self._last_time = log_time_display
        if self.show_level:
            row.append(level)

        if len(renderables) == 1 and isinstance(renderables[0], Text) and '\n' not in renderables[0].plain:
            row.append(Renderables(renderables))
            renderables = []
        else:
            row.append('')

        if self.show_path and path:
            path_text = Text()
            path_text.append(
                name, style=f"link file://{link_path}#{line_no}" if link_path else "",
            )
            row.append(path_text)

        output.add_row(*row)

        return Renderables([output] + renderables)  # type: ignore


ISO_FORMAT = '%Y-%m-%dT%H:%M:%S.%fZ'
RICH_TIME_FORMAT = '%H:%M:%S.%f'


log_console: Console | None = None

def get_rich_log_console() -> Console:
    global log_console

    if log_console is None:
        log_console = Console(stderr=True)
    return log_console


class RichLogHandler(RichHandler):
    _log_render: LogRender  # type: ignore[assignment]

    def __init__(self):
        super().__init__(log_time_format=RICH_TIME_FORMAT, console=get_rich_log_console(), rich_tracebacks=True)
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
        def add_scope(style: str, key: str):
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

        if scope_parts:
            out = Text()
            record.highlighter = None
            for part in scope_parts:
                out.append_text(part)
                out.append(' ')
            out.append_text(msg)
            msg = out

        return msg

    def render_message(self, record: LogRecord, message: str) -> ConsoleRenderable:
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
        log_time = datetime.fromtimestamp(record.created)

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
        )
        return log_renderable


class LogFmtFormatter(Logfmter):
    def __init__(self):
        keys = ['time', 'level', 'name']
        mapping = {
            'time': 'asctime',
            'level': 'levelname',
        }
        super().__init__(keys=keys, mapping=mapping, datefmt=ISO_FORMAT)

    def format(self, record: LogRecord) -> str:
        markup = getattr(record, 'markup', None)
        if isinstance(markup, bool) and markup:
            delattr(record, 'markup')
        if hasattr(record, '_extra_keys'):
            delattr(record, '_extra_keys')
        if markup and isinstance(record.msg, str):
            try:
                record.msg = Text.from_markup(record.msg).plain
            except Exception as e:
                print(e)
        return super().format(record)

    @classmethod
    def get_extra(cls, record: logging.LogRecord) -> dict:
        ret = super().get_extra(record)
        if 'taskName' in ret:
            del ret['taskName']
        if 'extra' in ret:
            del ret['extra']
        return ret

    def formatTime(self, record, datefmt=None):
        return datetime.fromtimestamp(record.created, UTC).strftime(ISO_FORMAT)


class UwsgiReqLogHandler(StreamHandler):
    def __init__(self, stream=None):
        if stream is None:
            stream = sys.stdout
        super().__init__(stream)

    def format(self, record: LogRecord) -> str:
        s = str(record.msg).rstrip('\n')
        return s

    def emit(self, record: LogRecord) -> None:
        # Only emit health check logs only for 5 mins after starting
        if ' path=/healthz' in record.msg:
            if record.relativeCreated > 5 * 60 * 1000:
                return
        print(self.format(record))


showwarning_ = warnings.showwarning
log_warning = logger.opt(depth=2)

def showwarning(message: Warning | str, category: type[Warning], filename: str, lineno: int, file=None, line=None):
    cat_str = '%s.%s' % (category.__module__, category.__name__)

    with log_warning.contextualize(category=cat_str):
        log_warning.warning(message)

if env_bool('LOG_WARNINGS', default=True):
    warnings.showwarning = showwarning


class LoguruLogRecord(LogRecord):
    def set_extra_keys(self, keys: list[str] | None):
        self._extra_keys = keys

    def pop_extra_keys(self) -> list[str] | None:
        if not hasattr(self, '_extra_keys'):
            return None
        keys = self._extra_keys
        delattr(self, '_extra_keys')
        return keys

logging.setLogRecordFactory(LoguruLogRecord)


class LoguruLogger(logging.Logger):
    def makeRecord(self, *args, **kwargs):
        rec = cast(LoguruLogRecord, super().makeRecord(*args, **kwargs))
        extra = args[8]
        if extra is not None and isinstance(extra, dict):
            rec.extra_keys = list(extra.keys())
            rec._extra_keys = list(extra.keys())
        return rec



def loguru_make_record(record: loguru.Record, strip_markup: bool = False):
    exc = record["exception"]
    extra = record.get('extra', {})
    name = extra.pop('name', record['name'] or '')

    msg = record['message']
    # We shouldn't pass `rich` markup
    if strip_markup and extra.pop('markup', False):
        msg = Text.from_markup(msg).plain

    log_rec = LoguruLogRecord(
        name,
        record["level"].no,
        record["file"].path,
        record["line"],
        msg.rstrip(),
        (),
        (exc.type, exc.value, exc.traceback) if exc else None, # type: ignore
        func=record["function"],
    )
    log_rec.set_extra_keys(list(record['extra'].keys()))
    if exc:
        log_rec.exc_text = "\n"
    return log_rec


rich_handler = RichLogHandler()
logfmt_formatter = LogFmtFormatter()


def loguru_rich_sink(message: loguru.Message):
    rec = loguru_make_record(message.record)
    rich_handler.acquire()
    try:
        rich_handler.emit(rec)
    finally:
        rich_handler.release()


def loguru_logfmt_sink(message: loguru.Message):
    rec = loguru_make_record(message.record, strip_markup=True)
    sys.stderr.write(logfmt_formatter.format(rec) + '\n')
    sys.stderr.flush()


class LoguruLoggingHandler(logging.Handler):
    def emit(self, record: LogRecord) -> None:
        # Figure out who the actual caller was
        depth = 0
        for fr, _ in traceback.walk_stack(sys._getframe().f_back):
            pkg_name = fr.f_globals['__name__'].split('.')[0]
            if pkg_name not in ('sentry_sdk', 'logging'):
                break
            depth += 1
            if depth == 10:
                break

        log = logger.opt(depth=depth + 1, exception=record.exc_info)
        extra_keys: list[str] | None = getattr(record, '_extra_keys', None)
        if extra_keys:
            extra = {key: getattr(record, key) for key in extra_keys if hasattr(record, key)}
            log = log.bind(**extra)
        log.log(record.levelname, record.getMessage())
