from __future__ import annotations

import logging
import sys
import threading
import traceback
import warnings
from datetime import UTC, datetime
from logging import LogRecord, StreamHandler
from typing import Any, cast

import loguru
from logfmter.formatter import Logfmter
from loguru import logger
from rich.text import Text

from kausal_common.deployment import env_bool
from kausal_common.logging.warnings import warning_traceback_enabled

ISO_FORMAT = '%Y-%m-%dT%H:%M:%S.%fZ'


class LogFmtFormatter(Logfmter):
    def __init__(self):
        mapping = {
            'time': 'asctime',
            'level': 'levelname',
            'thread.id': 'thread',
            'thread.name': 'threadName',
            'process.pid': 'process',
        }
        keys = ['time', 'level', 'name', 'process.pid', 'thread.id', 'thread.name']
        super().__init__(keys=keys, mapping=mapping, datefmt=ISO_FORMAT)

    def format(self, record: LogRecord) -> str:
        markup = getattr(record, 'markup', None)
        if isinstance(markup, bool) and markup:
            delattr(record, 'markup')
        if hasattr(record, '_extra_keys'):
            delattr(record, '_extra_keys')
        if record.thread:
            record.thread = threading.get_native_id()
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

    def formatTime(self, record: logging.LogRecord, datefmt=None) -> str:  # noqa: N802
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
        if ' path=/healthz' in record.msg and record.relativeCreated > 5 * 60 * 1000:
            return
        print(self.format(record))


showwarning_ = warnings.showwarning
log_warning = logger.opt(depth=2)


def showwarning(message: Warning | str, category: type[Warning], filename: str, lineno: int, file=None, line=None) -> None:
    cat_str = '%s.%s' % (category.__module__, category.__name__)

    with log_warning.contextualize(category=cat_str):
        log_warning.warning(message)


if not warning_traceback_enabled() and env_bool('LOG_WARNINGS', default=True):
    warnings.showwarning = showwarning


class LoguruLogRecord(LogRecord):
    def pop_extra_keys(self) -> list[str] | None:
        if not hasattr(self, '_extra_keys'):
            return None
        keys = self._extra_keys
        delattr(self, '_extra_keys')
        return keys

    def set_extra(self, extra: dict[str, Any]):
        self._extra_keys = list(extra.keys())
        for key, val in extra.items():
            if (key in ['message', 'asctime']) or (key in self.__dict__):
                raise KeyError('Attempt to overwrite %r in LogRecord' % key)
            setattr(self, key, val)


logging.setLogRecordFactory(LoguruLogRecord)


class LoguruLogger(logging.Logger):
    def makeRecord(self, *args, **kwargs):  # noqa: N802
        rec = cast('LoguruLogRecord', super().makeRecord(*args, **kwargs))
        extra = args[8]
        if extra is not None and isinstance(extra, dict):
            rec.extra_keys = list(extra.keys())
            rec._extra_keys = list(extra.keys())
        return rec


def loguru_make_record(record: loguru.Record, strip_markup: bool = False):
    exc = record['exception']
    extra = record.get('extra', {})
    name = extra.pop('name', record['name'] or '')

    msg = record['message']
    # We shouldn't pass `rich` markup
    if strip_markup and extra.get('markup', False):
        msg = Text.from_markup(msg).plain

    log_rec = LoguruLogRecord(
        name,
        record['level'].no,
        record['file'].path,
        record['line'],
        msg.rstrip(),
        (),
        (exc.type, exc.value, exc.traceback) if exc else None,  # type: ignore
        func=record['function'],
    )
    log_rec.set_extra(record['extra'])
    if exc:
        log_rec.exc_text = '\n'
    return log_rec


logfmt_formatter = LogFmtFormatter()


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
        logging_attrs = {}
        extra_keys: list[str] | None = getattr(record, '_extra_keys', None)
        if extra_keys:
            extra = {key: getattr(record, key) for key in extra_keys if hasattr(record, key)}
            logging_attrs.update(extra)
        if 'name' not in logging_attrs:
            logging_attrs['name'] = record.name
        log = log.bind(**logging_attrs)
        log.log(record.levelname, record.getMessage())


def loguru_logfmt_sink(message: loguru.Message):
    from kausal_common.sentry.logging import handle_log_record

    rec = loguru_make_record(message.record, strip_markup=True)

    sys.stderr.write(logfmt_formatter.format(rec) + '\n')
    sys.stderr.flush()
    handle_log_record(rec)
