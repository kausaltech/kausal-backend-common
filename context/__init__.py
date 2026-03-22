from __future__ import annotations

import sys
from importlib.util import find_spec
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from importlib.machinery import ModuleSpec

type DjangoProjectName = Literal['aplans', 'paths']
type KausalProjectId = Literal['paths-backend', 'watch-backend']

POSSIBLE_DJANGO_PROJECT_NAMES: tuple[DjangoProjectName, ...] = ('aplans', 'paths')


def get_django_project_name() -> DjangoProjectName:
    specs: list[tuple[DjangoProjectName, ModuleSpec | None]] = []
    for project_name in POSSIBLE_DJANGO_PROJECT_NAMES:
        spec = find_spec(project_name)
        if spec is not None:
            specs.append((project_name, spec))
    if len(specs) > 1:
        raise RuntimeError(f'Multiple Django projects found: {specs} (PYTHONPATH: {sys.path})')
    if len(specs) == 0:
        raise RuntimeError(f'No Django project found (PYTHONPATH: {sys.path})')
    return specs[0][0]


def get_product_name() -> str:
    project_name = get_django_project_name()
    if project_name == 'paths':
        return 'Kausal Paths'
    if project_name == 'aplans':
        return 'Kausal Watch'
    raise ValueError(f'Unknown project: {project_name}')


def get_project_id() -> KausalProjectId:
    if get_django_project_name() == 'paths':
        return 'paths-backend'
    if get_django_project_name() == 'aplans':
        return 'watch-backend'
    raise ValueError('Unknown project')
