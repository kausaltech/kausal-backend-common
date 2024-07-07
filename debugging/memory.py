from __future__ import annotations
from tracemalloc import Snapshot

from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rich import print


previous_snap: Snapshot | None = None


@api_view(['GET'])
@permission_classes([])
def memory_trace(request):
    global previous_snap
    import tracemalloc
    import gc
    before = [x / 1024 / 1024 for x in tracemalloc.get_traced_memory()]
    gc.collect()
    after = [x / 1024 / 1024 for x in tracemalloc.get_traced_memory()]
    snap = tracemalloc.take_snapshot()
    if previous_snap:
        stats = snap.compare_to(previous_snap, 'traceback')
        for s in stats[0:10]:
            print(s)
            for line in s.traceback.format(most_recent_first=True):
                print(line)
    else:
        stats = None
    previous_snap = snap

    return Response({
        'before': {'current': before[0], 'peak': before[1]},
        'after': {'current': after[0], 'peak': after[1]},
        'stats': [str(s) for s in stats[:10]] if stats else None
    })
