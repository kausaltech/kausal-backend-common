from __future__ import annotations  # noqa: INP001

import multiprocessing
import os

from kausal_common.deployment import env_bool
from kausal_common.deployment.gunicorn import get_gunicorn_hooks

bind = "0.0.0.0:8000"
#workers = min(multiprocessing.cpu_count() * 2 + 1, 4)
workers = 2
threads = multiprocessing.cpu_count() * 2 + 1
wsgi_app = '%s.wsgi:application' % os.environ['DJANGO_PROJECT']
forwarded_allow_ips = '*'

KUBE_MODE = env_bool('KUBERNETES_MODE', default=False)
TEST_MODE = env_bool('TEST_MODE', default=False)

if KUBE_MODE or TEST_MODE:
    preload_app = True

if KUBE_MODE or os.getenv('KUBERNETES_LOGGING', '') == '1':
    logger_class = 'kausal_common.logging.gunicorn.Logger'
else:
    access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'
    accesslog = '-'

locals().update(get_gunicorn_hooks())
