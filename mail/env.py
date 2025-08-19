from __future__ import annotations

# kwargs to be added to arguments to django-environ's Env.__init__()
ENV_SCHEMA = dict(
    ALLOWED_SENDER_EMAILS=(list, []),
    SERVER_EMAIL=(str, ''),
    DEFAULT_FROM_EMAIL=(str, 'noreply@mj.kausal.tech'),
    DEFAULT_FROM_NAME=(str, 'Kausal'),
    MAILGUN_API_KEY=(str, ''),
    MAILGUN_SENDER_DOMAIN=(str, ''),
    MAILGUN_REGION=(str, ''),
    MAILJET_API_KEY=(str, ''),
    MAILJET_SECRET_KEY=(str, ''),
    SENDGRID_API_KEY=(str, ''),
    ALLOWED_RECIPIENT_EMAIL_DOMAINS=(list, []),
)
