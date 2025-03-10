import importlib
from kausal_common.context import get_django_project_name

project_name = get_django_project_name()
dataset_config = importlib.import_module(f'{project_name}.dataset_config')
