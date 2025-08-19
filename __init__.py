from __future__ import annotations

from typing import Any

from .mail.env import ENV_SCHEMA as MAIL_ENV_SCHEMA

# kwargs to be added to arguments to django-environ's Env.__init__()
ENV_SCHEMA = dict(
    **MAIL_ENV_SCHEMA,
)


def register_settings(settings: dict[str, Any]):
    from .mail.settings import register_settings as register_mail_settings
    register_mail_settings(settings)
    settings['FORMS_URLFIELD_ASSUME_HTTPS'] = True
