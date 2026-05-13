"""
MJML email rendering.

Renders Jinja2 + MJML templates from ``kausal_common/notifications/mjml-templates``
(or any registered template root) via the system-installed ``mjml`` CLI.
The CLI is expected at ``node_modules/.bin/mjml`` relative to ``BASE_DIR``;
this matches the dev setup used by both Watch and Paths.
"""

import logging
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from django.conf import settings
from django.utils.formats import date_format
from django.utils.translation import get_language
from django.utils.translation.trans_real import DjangoTranslation

from jinja2 import FileSystemLoader, StrictUndefined
from jinja2.sandbox import SandboxedEnvironment
from sentry_sdk import capture_exception

if TYPE_CHECKING:
    from collections.abc import Sequence

logger = logging.getLogger(__name__)


_DEFAULT_TEMPLATE_DIR = str(Path(__file__).parent / 'mjml-templates')


def _mjml_cmd() -> list[str]:
    return [
        str(Path(settings.BASE_DIR) / 'node_modules' / '.bin' / 'mjml'),
        '-c',
        'ignoreIncludes=true',
        '--config.validationLevel',
        'strict',
        '-i',
        '-s',
    ]


def make_jinja_environment(
    template_dirs: Sequence[str] | None = None,
    translations_domain: str = 'notifications',
) -> SandboxedEnvironment:
    dirs = list(template_dirs) if template_dirs else [_DEFAULT_TEMPLATE_DIR]
    env = SandboxedEnvironment(
        trim_blocks=True,
        lstrip_blocks=True,
        undefined=StrictUndefined,
        loader=FileSystemLoader(dirs),
        extensions=['jinja2.ext.i18n'],
    )
    trans = DjangoTranslation(get_language(), translations_domain)
    env.install_gettext_callables(  # type: ignore[attr-defined]
        gettext=trans.gettext,
        ngettext=trans.ngettext,
        newstyle=True,
    )
    env.filters['format_date'] = date_format
    return env


def render_mjml(mjml_in: str, dump: str | None = None) -> str:
    try:
        proc = subprocess.run(  # noqa: S603  # mjml CLI path is built from BASE_DIR, not user input
            _mjml_cmd(),
            input=mjml_in,
            capture_output=True,
            encoding='utf8',
            check=True,
        )
    except subprocess.CalledProcessError as e:
        logger.error(e.stderr)
        capture_exception(e)
        raise

    if dump:
        with Path('%s.mjml' % dump).open('w', encoding='utf8') as f:
            f.write(mjml_in)
        with Path('%s.html' % dump).open('w', encoding='utf8') as f:
            f.write(proc.stdout)

    if proc.stderr:
        logger.warning('Warnings from MJML:\n%s' % proc.stderr)
    return proc.stdout


def render_mjml_from_template(
    template_name: str,
    context: dict[str, object],
    template_dirs: Sequence[str] | None = None,
    translations_domain: str = 'notifications',
    dump: str | None = None,
) -> str:
    env = make_jinja_environment(template_dirs=template_dirs, translations_domain=translations_domain)
    template = env.get_template('%s.mjml' % template_name)
    return render_mjml(template.render(context), dump=dump)
