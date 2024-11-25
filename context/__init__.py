from __future__ import annotations

from importlib.util import find_spec
from typing import Literal, cast

type DjangoProjectName = Literal['aplans', 'paths']

def get_django_project_name() -> DjangoProjectName:
    for project_name in ('aplans', 'paths'):
        spec = find_spec(project_name)
        if spec is not None:
            return cast(DjangoProjectName, project_name)
    raise RuntimeError('No Django project found')


def get_product_name() -> str:
    project_name = get_django_project_name()
    if project_name == 'paths':
        return 'Kausal Paths'
    if project_name == 'aplans':
        return 'Kausal Watch'
    raise ValueError(f'Unknown project: {project_name}')
