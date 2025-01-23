# ruff: noqa: N806
from __future__ import annotations


def register_settings(settings: dict):
    # All local variables here (except `settings` itself) will be put in `settings`
    # Pull some out for convenience
    env = settings['env']
    DEBUG = settings['DEBUG']

    settings['INSTALLED_APPS'].append('anymail')

    ALLOWED_SENDER_EMAILS = env('ALLOWED_SENDER_EMAILS')
    SERVER_EMAIL = env('SERVER_EMAIL')
    if not SERVER_EMAIL and ALLOWED_SENDER_EMAILS:
        SERVER_EMAIL = ALLOWED_SENDER_EMAILS[0]
    DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL')
    if not DEFAULT_FROM_EMAIL and ALLOWED_SENDER_EMAILS:
        DEFAULT_FROM_EMAIL = ALLOWED_SENDER_EMAILS[0]
    DEFAULT_FROM_NAME = env('DEFAULT_FROM_NAME')

    EMAIL_BACKEND = 'anymail.backends.console.EmailBackend'
    ANYMAIL = {}

    if env.str('MAILGUN_API_KEY'):
        EMAIL_BACKEND = 'anymail.backends.mailgun.EmailBackend'
        ANYMAIL['MAILGUN_API_KEY'] = env.str('MAILGUN_API_KEY')
        ANYMAIL['MAILGUN_SENDER_DOMAIN'] = env.str('MAILGUN_SENDER_DOMAIN')
        if env.str('MAILGUN_REGION'):
            ANYMAIL['MAILGUN_API_URL'] = 'https://api.%s.mailgun.net/v3' % env.str('MAILGUN_REGION')

    if env.str('SENDGRID_API_KEY'):
        EMAIL_BACKEND = 'anymail.backends.sendgrid.EmailBackend'
        ANYMAIL['SENDGRID_API_KEY'] = env.str('SENDGRID_API_KEY')

    if env.str('MAILJET_API_KEY'):
        EMAIL_BACKEND = 'anymail.backends.mailjet.EmailBackend'
        ANYMAIL['MAILJET_API_KEY'] = env.str('MAILJET_API_KEY')
        ANYMAIL['MAILJET_SECRET_KEY'] = env.str('MAILJET_SECRET_KEY')

    if DEBUG:
        EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

    settings.update({key: value for key, value in locals().items() if key != 'settings'})
