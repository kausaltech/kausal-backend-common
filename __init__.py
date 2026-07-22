from __future__ import annotations

import os
from typing import Any, Literal

from .mail.env import ENV_SCHEMA as MAIL_ENV_SCHEMA

# kwargs to be added to arguments to django-environ's Env.__init__()
ENV_SCHEMA = dict(
    **MAIL_ENV_SCHEMA,
)


def register_settings(settings: dict[str, Any]):
    from .debugging import init_debugger
    from .mail.settings import register_settings as register_mail_settings

    register_mail_settings(settings)
    init_debugger()


_JEMALLOC_CONF = 'dirty_decay_ms:500,muzzy_decay_ms:0'


def _early_init() -> None:
    # This has to be set for polars; otherwise the process' RSS will grow indefinitely.
    # Also, it has to be set before polars gets imported.
    # See: https://github.com/pola-rs/polars/issues/23128
    if old_val := os.getenv('_RJEM_MALLOC_CONF'):
        if not old_val.endswith(_JEMALLOC_CONF):
            raise RuntimeError(f'Invalid jemalloc configuration. Found: `{old_val}`)')
    else:
        os.environ['_RJEM_MALLOC_CONF'] = _JEMALLOC_CONF


IS_MYPY: Literal[False] = False

_early_init()
