from __future__ import annotations

import os
import gc
import time
from typing import Any

from django.core.cache import caches
from django.db import connections
from loguru import logger
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response


def check_database():
    conn = connections['default']
    conn_time_left = None
    start = time.monotonic()
    try:
        with conn.cursor() as cursor:
            if not cursor.db.is_usable():
                logger.error("Database connection unusable")
                return dict(status='fail')
            if cursor.db.close_at is not None:
                conn_time_left = round(cursor.db.close_at - start, 1)
    except Exception:
        logger.exception("Database health check error")
        return dict(status='fail')
    latency = round((time.monotonic() - start) * 1000000)
    return dict(status='pass', conn_time_left=conn_time_left, latency_us=latency)


def check_cache() -> dict:
    start = time.monotonic()
    cache = caches['default']
    resp = cache.get_or_set('health-check', default='checked', timeout=1)
    latency = round((time.monotonic() - start) * 1000000)
    if resp == 'checked':
        return dict(status='pass', latency_us=latency)
    logger.error("Cache check failed (cache returned '%s' instead of '%s')" % (resp, 'checked'))
    return dict(status='fail')


def check_garbage_collection() -> dict:
    nr_unreachable = gc.collect()
    # if nr_unreachable:
    #     logger.error("Garbage collection identified %d unreachable objects" % nr_unreachable)
    #     return dict(status='fail')
    return dict(status='pass', nr_unreachable=nr_unreachable)


@api_view(['GET'])
@permission_classes([])
def health_view(request):
    # TODO: Implement checks
    # https://tools.ietf.org/id/draft-inadarei-api-health-check-05.html

    checks: dict[str, Any] = {}

    checks['database'] = check_database()
    checks['cache'] = check_cache()
    checks['gc'] =  check_garbage_collection()
    resp = {
        'status': 'pass',
        'checks': checks,
        'pid': os.getpid(),
    }

    return Response(resp)
