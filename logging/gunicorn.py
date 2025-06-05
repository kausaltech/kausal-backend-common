from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from django.conf import settings

from gunicorn.glogging import Logger as BaseLogger

if TYPE_CHECKING:
    from datetime import timedelta

    from gunicorn.http.message import Request
    from gunicorn.http.wsgi import Response

access_log = logging.getLogger('gunicorn.access')
error_log = logging.getLogger('gunicorn.error')

class Logger(BaseLogger):
    def setup(self, cfg):
        super().setup(cfg)
        self.error_log = error_log
        self.access_log = access_log

    def access(self, resp: Response, req: Request, environ: dict[str, str], request_time: timedelta):
        status: int | None = resp.status_code
        level = 'INFO'
        if isinstance(status, int):
            if status >= 500 and settings.DEBUG:
                level = 'ERROR'
            if status >= 400:
                level = 'WARNING'
        level_map = logging.getLevelNamesMapping()
        remote_addr = req.remote_addr
        if isinstance(remote_addr, tuple):
            remote_addr = ':'.join(str(x) for x in remote_addr)
        args = dict(
            method=req.method,
            path=req.path,
            host=req.uri,
            http_status=resp.status_code,
            remote_ip=remote_addr,
            response_time_ms=round(request_time.total_seconds() * 1000, 1),
            response_size=resp.sent,
            request_body_size=len(req.body.buf.getbuffer()),
            user_agent=environ.get('HTTP_USER_AGENT'),
        )
        access_log.log(level_map[level], '%s %s' % (req.method, req.path), extra=args)
