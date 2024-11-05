from __future__ import annotations

import os
from importlib.util import find_spec

import django


def init_django() -> None:
    if find_spec('aplans'):
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aplans.settings')
    elif find_spec('paths'):
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'paths.settings')
    else:
        raise RuntimeError('No settings module found')

    django.setup()
