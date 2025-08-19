from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any

    from django.core.mail.message import EmailMessage


def _filter_recipient_email(sender: Any, message: EmailMessage, **kwargs) -> None:  # pyright: ignore[reportUnusedParameter]
    from django.conf import settings

    from anymail.exceptions import AnymailCancelSend
    from loguru import logger

    logger = logger.bind(name='kausal_common.mail')

    domains: set[str] = set(settings.ALLOWED_RECIPIENT_EMAIL_DOMAINS)

    def validate_email(email: str) -> None:
        domain = email.split('@')[1].lower()
        if domain not in domains:
            logger.warning(f'Email domain {domain} not in allowed domains: {domains}')
            raise AnymailCancelSend(f'Email domain {domain} not in allowed domains: {domains}')

    for to in message.to:
        validate_email(to)
    for cc in message.cc:
        validate_email(cc)
    for bcc in message.bcc:
        validate_email(bcc)


def register_signal_handlers():
    from django.conf import settings

    from anymail.signals import pre_send

    if settings.ALLOWED_RECIPIENT_EMAIL_DOMAINS:
        pre_send.connect(receiver=_filter_recipient_email)
