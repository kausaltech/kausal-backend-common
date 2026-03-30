from __future__ import annotations

import gc
import os
import time

from django.core.cache import caches
from django.db import connections
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_GET
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

import psutil
import sentry_sdk
from loguru import logger

from .limits import MemoryLimit

HEALTH_CHECK_VIEW_NAMES = ('liveness', 'readiness', 'healthcheck')

TRUSTED_CIDRS = [
    '10.0.0.0/8',
    '172.16.0.0/12',
    '192.168.0.0/16',
    '127.0.0.1/32',
]


def check_database():
    conn = connections['default']
    conn_time_left = None
    start = time.monotonic()
    try:
        with conn.cursor() as cursor:
            if not cursor.db.is_usable():
                logger.error('Database connection unusable')
                return dict(status='fail')
            if cursor.db.close_at is not None:
                conn_time_left = round(cursor.db.close_at - start, 1)
    except Exception as e:
        logger.exception('Database health check error')
        sentry_sdk.capture_exception(e)
        return dict(status='fail')
    latency = round((time.monotonic() - start) * 1000000)
    return dict(status='pass', conn_time_left=conn_time_left, latency_us=latency)


def check_cache() -> dict:
    start = time.monotonic()
    cache = caches['default']
    try:
        resp = cache.get_or_set('health-check', default='checked', timeout=1)
    except Exception as e:
        sentry_sdk.capture_exception(e)
        logger.exception('Cache health check error')
        return dict(status='fail')

    latency = round((time.monotonic() - start) * 1000000)
    if resp == 'checked':
        return dict(status='pass', latency_us=latency)

    logger.error("Cache check failed (cache returned '%s' instead of '%s')" % (resp, 'checked'))
    return dict(status='fail')


def check_garbage_collection() -> dict:
    out: dict = dict(status='pass')
    nr_unreachable = gc.collect()
    out['nr_unreachable'] = nr_unreachable
    # if nr_unreachable:
    #     logger.error("Garbage collection identified %d unreachable objects" % nr_unreachable)
    #     return dict(status='fail')
    return out


def check_ram_usage(pre_gc: MemoryLimit | None = None) -> dict:
    cram = MemoryLimit.from_cgroup()
    out: dict = dict(
        status='pass',
    )
    if cram is not None:
        out['container'] = dict(
            current=cram.current_mib,
            limit=cram.max_usage_mib,
        )

    process = MemoryLimit.from_psutil()
    out['process'] = dict(
        current=process.current_mib,
    )

    worker_process = psutil.Process(os.getpid())
    parent = worker_process.parent()
    workers = []
    total_ram = 0
    known_parent_prefices = ('gunicorn', 'uwsgi', 'python')
    is_coordinator = any(parent.name().startswith(pfx) for pfx in known_parent_prefices) if parent else False
    if is_coordinator and parent:
        for child in parent.children(recursive=True):
            mem = MemoryLimit.from_psutil(child.pid)
            workers.append(dict(pid=child.pid, rss_mib=mem.current_mib))
            total_ram += mem.current_mib
    if workers:
        out['workers'] = workers
        out['workers_total_mib'] = total_ram

    return out


@require_GET
def liveness_view(request):
    """Liveness: just prove the worker can respond. No DB, no cache, no GC."""
    return HttpResponse(b'ok', content_type='text/plain')


@require_GET
def readiness_view(request):
    """Readiness: check dependencies, but skip expensive introspection."""
    checks = {}
    checks['database'] = check_database()
    checks['cache'] = check_cache()

    status = 'pass' if all(c.get('status') == 'pass' for c in checks.values()) else 'fail'
    http_status = 200 if status == 'pass' else 503

    return JsonResponse(
        {'status': status, 'checks': checks, 'pid': os.getpid()},
        status=http_status,
    )


def is_internal_ip(ip: str) -> bool:
    from ipaddress import ip_address, ip_network

    addr = ip_address(ip)
    return any(addr in ip_network(cidr) for cidr in TRUSTED_CIDRS)


@api_view(['GET'])
@permission_classes([])
def diagnostics_view(request):
    if not is_internal_ip(request.META.get('REMOTE_ADDR', '')):
        raise PermissionDenied('Not accessible externally')
    checks = {}
    with sentry_sdk.start_span(op='diagnostics.check', name='database'):
        checks['database'] = check_database()
    with sentry_sdk.start_span(op='diagnostics.check', name='cache'):
        checks['cache'] = check_cache()
    with sentry_sdk.start_span(op='diagnostics.check', name='gc.collect'):
        checks['gc'] = check_garbage_collection()
    with sentry_sdk.start_span(op='diagnostics.check', name='ram_usage'):
        checks['memory'] = check_ram_usage()
    return Response(checks)
