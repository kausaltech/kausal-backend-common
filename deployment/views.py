import time
from typing import Any
from loguru import logger
from django.db import connections
from django.core.cache import caches
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response


def check_database():
    conn = connections['default']
    conn_age = None
    now = time.monotonic()
    try:
        with conn.cursor() as cursor:
            if not cursor.db.is_usable():
                logger.error("Database connection unusable")
                return dict(status='fail')
            if cursor.db.close_at is not None:
                conn_age = now - cursor.db.close_at
    except Exception:
        logger.exception("Database health check error")
        return dict(status='fail')
    return dict(status='pass', conn_age=conn_age)


def check_cache() -> dict:
    cache = caches['default']
    resp = cache.get_or_set('health-check', default='checked', timeout=1)
    if resp == 'checked':
        return dict(status='pass')
    logger.error("Cache check failed (cache returned '%s' instead of '%s')" % resp)
    return dict(status='fail')


@api_view(['GET'])
@permission_classes([])
def health_view(request):
    # TODO: Implement checks
    # https://tools.ietf.org/id/draft-inadarei-api-health-check-05.html

    checks: dict[str, Any] = {}

    checks['database'] = check_database()
    checks['cache'] = check_cache()
    resp = {
        'status': 'pass',

        'checks': checks,
    }

    return Response({
        'status': 'pass',
        'checks': checks,
    })
