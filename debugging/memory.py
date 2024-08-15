from __future__ import annotations

import tracemalloc
from tracemalloc import Snapshot

from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from rich import print

previous_snap: Snapshot | None = None


@api_view(['GET'])
@permission_classes([])
def memory_trace(request):
    global previous_snap

    if not settings.DEBUG:
        raise PermissionDenied()

    if not tracemalloc.is_tracing():
        tracemalloc.start(10)

    snap = tracemalloc.take_snapshot()
    if previous_snap:
        stats = snap.compare_to(previous_snap, 'traceback')
        for s in stats[0:10]:
            print('\n')
            print(s)
            for line in s.traceback.format(most_recent_first=True):
                print(line)
    else:
        stats = None
    previous_snap = snap

    return Response({
        'stats': [str(s) for s in stats[:10]] if stats else None,
    })
