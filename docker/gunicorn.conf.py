from __future__ import annotations  # noqa: INP001

import multiprocessing
import os

from kausal_common.context import get_django_project_name
from kausal_common.deployment import env_bool
from kausal_common.deployment.gunicorn import get_gunicorn_hooks

bind = "0.0.0.0:8000"
#workers = min(multiprocessing.cpu_count() * 2 + 1, 4)
KUBE_MODE = env_bool('KUBERNETES_MODE', default=False)
TEST_MODE = env_bool('TEST_MODE', default=False)
# Use only one worker in test mode to avoid process isolation issues
if TEST_MODE:
    workers = 1
else:
    workers = 2
threads = multiprocessing.cpu_count() * 2 + 1
wsgi_app = '%s:application' % os.getenv('UWSGI_MODULE', f'{get_django_project_name()}.wsgi')

try:
    import uvicorn  # noqa: F401
except ImportError:
    pass
else:
    worker_class = 'uvicorn.workers.UvicornWorker'
    wsgi_app = '%s:application' % os.getenv('ASGI_MODULE', f'{get_django_project_name()}.asgi')

forwarded_allow_ips = '*'

if False and (KUBE_MODE or TEST_MODE):  # noqa: SIM223
    # No preloading until Python 3.14; Polars will deadlock otherwise
    preload_app = True

if KUBE_MODE or env_bool('KUBERNETES_LOGGING', default=False):
    logger_class = 'kausal_common.logging.gunicorn.Logger'
else:
    access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'
    accesslog = '-'

locals().update(get_gunicorn_hooks())
