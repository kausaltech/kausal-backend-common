from __future__ import annotations

from importlib.util import find_spec


def get_django_project_name() -> str:
    for project_name in ('aplans', 'paths'):
        spec = find_spec(project_name)
        if spec is not None:
            return project_name
    raise RuntimeError('No Django project found')
