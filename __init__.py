from __future__ import annotations

from .mail.env import ENV_SCHEMA as MAIL_ENV_SCHEMA

# Used in ENV_SCHEMA -- all of these environment variables will be exposed as variables in `settings`
EXPOSED_SETTINGS_ENV_SCHEMA = dict(
    # for future settings; example:
    # FOO=(bool, False),
)

# kwargs to be added to arguments to django-environ's Env.__init__()
ENV_SCHEMA = dict(
    **EXPOSED_SETTINGS_ENV_SCHEMA,
    **MAIL_ENV_SCHEMA,
)


def register_settings(settings: dict):
    from .mail.settings import register_settings as register_mail_settings
    register_mail_settings(settings)
    settings['FORMS_URLFIELD_ASSUME_HTTPS'] = True

    # Expose variables from EXPOSED_SETTINGS_ENV_SCHEMA to `settings`
    env = settings['env']
    for var in EXPOSED_SETTINGS_ENV_SCHEMA.keys():
        settings[var] = env(var)
