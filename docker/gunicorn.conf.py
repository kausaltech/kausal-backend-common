from __future__ import annotations  # noqa: INP001

import multiprocessing
import os

from kausal_common.context import get_django_project_name
from kausal_common.deployment import env_bool, env_int
from kausal_common.deployment.gunicorn import get_gunicorn_hooks

bind = '0.0.0.0:8000'
# workers = min(multiprocessing.cpu_count() * 2 + 1, 4)
KUBE_MODE = env_bool('KUBERNETES_MODE', default=False)
TEST_MODE = env_bool('TEST_MODE', default=False)
# Use only one worker in test mode to avoid process isolation issues


workers_env = os.getenv('GUNICORN_WORKERS', None)
if workers_env:
    try:
        workers = int(workers_env)
    except ValueError:
        workers_env = None

if not workers_env:
    if TEST_MODE:
        workers = 1
    else:
        workers = 2
        # Recycle workers periodically to bound memory growth in long-running processes.
        #
        # Keep this generous. When PROMETHEUS_MULTIPROC_DIR is set, every worker that exits
        # leaves behind counter_<pid>.db and histogram_<pid>.db, which prometheus_client
        # retains on purpose so cumulative totals survive the recycle. Nothing reclaims them
        # for the life of the pod, and MultiProcessCollector re-reads all of them on every
        # scrape -- so aggressive recycling degrades the metrics endpoint over time. Measured
        # on Watch production with max_requests=1000: ~69 dead workers/day, 1804 files and
        # 132 MiB after 13 days, with collection time growing from 0.05s to 0.7-1.2s and the
        # metrics sidecar being liveness-killed once it crossed 1s.
        max_requests = env_int('GUNICORN_MAX_REQUESTS', default=5000)
        max_requests_jitter = env_int('GUNICORN_MAX_REQUESTS_JITTER', default=1000)

threads = multiprocessing.cpu_count() * 2 + 1
wsgi_app = '%s:application' % os.getenv('UWSGI_MODULE', f'{get_django_project_name()}.wsgi')

try:
    import uvicorn  # noqa: F401  # pyright: ignore[reportUnusedImport]
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
