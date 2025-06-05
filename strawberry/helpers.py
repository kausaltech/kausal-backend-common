from __future__ import annotations

from typing import Literal

from loguru import logger

logger = logger.bind(markup=True, name='graphql')

type LogLevel = Literal['DEBUG', 'INFO', 'SUCCESS', 'WARNING', 'ERROR', 'CRITICAL']


def graphql_log(level: LogLevel, operation_name: str | None, msg, *args, depth: int = 0, **kwargs):
    log = logger.opt(depth=1 + depth)
    if operation_name:
        log = log.bind(graphql_operation=operation_name)
    log.log(level, 'GQL request [magenta]%s[/]: %s' % (operation_name, msg), *args, **kwargs)
