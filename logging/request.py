from __future__ import annotations

import contextlib
import hashlib
import time
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, overload

import nanoid
import sentry_sdk
from loguru import logger

from kausal_common.const import FORWARDED_FOR_HEADER, FORWARDED_HEADER, REQUEST_CORRELATION_ID_HEADER
from kausal_common.deployment import env_bool
from kausal_common.deployment.http import parse_forwarded
from kausal_common.deployment.types import get_cluster_context
from kausal_common.logging.rich_logger import styled_http_method

if TYPE_CHECKING:
    from collections.abc import Callable, Generator, Iterable

    from django.http.request import HttpRequest

    from kausal_common.asgi.types import ASGICommonScope
    from kausal_common.deployment.types import LoggedHttpRequest

    from users.models import User


ID_ALPHABET = '346789ABCDEFGHJKLMNPQRTUVWXYabcdefghijkmnpqrtwxyz'

logger = logger.bind(name='request', markup=True)


@dataclass
class RequestCommonMeta:
    """
    Common metadata for all ASGI and WSGI requests.

    It is used e.g. to contextualize log lines and sentry events.
    """

    correlation_id: str
    """Randomly generated correlation ID for the request."""

    client_ip: str | None = None
    """Client IP address."""

    user: User | None = None
    """User associated with the request."""

    session_id: str | None = None
    """Django session ID."""

    http_method: str | None = None
    """HTTP method."""

    http_path: str | None = None
    """HTTP path."""

    request_body_size: int | None = None
    """Size of the request body."""

    user_agent: str | None = None
    """User agent of the request."""

    ws_verb: str | None = None
    """WebSocket verb."""

    referer: str | None = None
    """Referer."""

    @staticmethod
    def generate_correlation_id() -> str:
        return nanoid.non_secure_generate(ID_ALPHABET, 8)

    @classmethod
    def _get_client_ip_from_request(cls, request: HttpRequest) -> str | None:
        forwarded = request.headers.get(FORWARDED_HEADER)
        if forwarded:
            fwd_vals = parse_forwarded([forwarded])
            if fwd_vals and fwd_vals[0].for_:
                return fwd_vals[0].for_
        x_fwd = request.headers.get(FORWARDED_FOR_HEADER)
        if x_fwd:
            return x_fwd.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')

    @classmethod
    def _get_correlation_id(cls) -> str:
        return cls.generate_correlation_id()

    @classmethod
    def _get_session_id(cls, session_id: str) -> str:
        return hashlib.md5(session_id.encode('utf-8'), usedforsecurity=False).hexdigest()[0:8]

    @classmethod
    def from_request(cls, request: LoggedHttpRequest) -> RequestCommonMeta:
        from kausal_common.users import user_or_none

        session_id = request.session.session_key if request.session else None
        if session_id:
            session_id = cls._get_session_id(session_id)
        correlation_id = request.headers.get(REQUEST_CORRELATION_ID_HEADER)
        if correlation_id is None:
            correlation_id = cls._get_correlation_id()
            request.correlation_id = correlation_id

        content_length = request.headers.get('content-length')
        request_body_size = None
        if content_length:
            with contextlib.suppress(Exception):
                request_body_size = int(content_length)

        return RequestCommonMeta(
            correlation_id=correlation_id,
            client_ip=cls._get_client_ip_from_request(request),
            user=user_or_none(request.user),
            session_id=session_id,
            http_method=request.method,
            http_path=request.path,
            user_agent=request.headers.get('x-original-user-agent') or request.headers.get('user-agent'),
            request_body_size=request_body_size,
            referer=request.headers.get('referer'),
        )

    @classmethod
    def from_scope(cls, scope: ASGICommonScope) -> RequestCommonMeta:
        from kausal_common.users import user_or_none

        session = scope.get('session')
        session_id = session.session_key if session else None
        if session_id:
            session_id = cls._get_session_id(session_id)
        correlation_id = scope.get('correlation_id')
        if correlation_id is None:
            correlation_id = cls._get_correlation_id()
            scope['correlation_id'] = correlation_id
        client = scope.get('client')
        if client:
            client_ip = client[0]
        else:
            client_ip = None
        if scope.get('type') == 'http':
            http_method = scope.get('method')
        else:
            http_method = None
        if scope.get('type') == 'websocket':
            ws_verb = 'message'
        else:
            ws_verb = None
        headers = scope.get('headers', [])
        referer = None
        for key, value in headers:
            if key == b'referer':
                referer = value.decode('utf-8')
                break
        return cls(
            correlation_id=correlation_id,
            client_ip=client_ip,
            user=user_or_none(scope.get('user')),
            session_id=session_id,
            http_method=http_method,
            ws_verb=ws_verb,
            referer=referer,
        )

    def get_full_log_context(self) -> dict[str, str | int]:
        ctx: dict[str, str | int] = {
            'correlation_id': self.correlation_id,
        }

        span = sentry_sdk.get_current_span()
        if span and span.trace_id:
            ctx['trace.id'] = span.trace_id
            ctx['trace.sampled'] = str(span.sampled)

        if self.client_ip:
            ctx['client.address'] = self.client_ip
        if self.user:
            ctx['user.email'] = self.user.email
            ctx['user.id'] = str(self.user.uuid)
        if self.session_id:
            ctx['session.id'] = self.session_id
        if self.referer:
            ctx['http.request.referer'] = self.referer
        if self.http_path:
            ctx['http.request.path'] = self.http_path
        if self.user_agent:
            ctx['user_agent.original'] = self.user_agent
        if self.request_body_size is not None:
            ctx['http.request.body_size'] = self.request_body_size
        if self.http_path:
            ctx['url.path'] = self.http_path

        return ctx

    def to_log_context(self) -> dict[str, str]:
        ctx = {'correlation_id': self.correlation_id}
        if self.user:
            ctx['user.id'] = str(self.user.uuid)
        return ctx

    def get_sentry_user_data(self) -> dict[str, str] | None:
        from kausal_common.users import user_or_none

        user_data: dict[str, str] = {}
        if self.client_ip:
            user_data['ip_address'] = self.client_ip
        user = user_or_none(self.user)
        if user:
            user_data['id'] = str(user.uuid)
            user_data['email'] = user.email
        return user_data if user_data else None

    def _enter_viztracer_stack(self, stack: ExitStack, operation_name: str) -> None:
        from django.db import connection

        from viztracer import VizTracer  # type: ignore

        def trace_sql_query(
            execute: Callable[..., Any], sql: str, params: Iterable[Any], many: bool, context: dict[str, Any]
        ) -> Any:
            with tracer.log_event('sql_query'):
                res = execute(sql, params, many, context)
            return res

        now_ts = datetime.now().strftime('%Y%m%d_%H%M%S')  # noqa: DTZ005
        Path('perf-traces').mkdir(exist_ok=True)
        trace_fn = f'perf-traces/{operation_name}_{now_ts}.json'
        tracer = VizTracer(output_file=trace_fn, max_stack_depth=60, log_async=True, tracer_entries=3000000)
        stack.enter_context(tracer)
        stack.enter_context(connection.execute_wrapper(trace_sql_query))
        logger.info(f'Saving trace to {trace_fn}')

    @contextmanager
    def contextualize_logger(self) -> Generator[None]:
        with logger.contextualize(**self.to_log_context()):
            _rich_traceback_omit = True
            yield

    @contextmanager
    def with_sentry_context(self) -> Generator[sentry_sdk.Scope]:
        with sentry_sdk.new_scope() as scope:
            _rich_traceback_omit = True
            sentry_sdk.set_user(self.get_sentry_user_data())
            scope.set_context('request', dict(correlation_id=self.correlation_id))
            cluster_context = get_cluster_context()
            for key, value in cluster_context.items():
                if value:
                    sentry_sdk.set_tag(key, value)
            yield scope

    @overload
    @contextmanager
    def start_request(self, *, request: LoggedHttpRequest) -> Generator[sentry_sdk.Scope]: ...

    @overload
    @contextmanager
    def start_request(self, *, scope: ASGICommonScope) -> Generator[sentry_sdk.Scope]: ...

    @contextmanager
    def start_request(
        self, *, request: LoggedHttpRequest | None = None, scope: ASGICommonScope | None = None
    ) -> Generator[sentry_sdk.Scope]:
        from kausal_common.users import user_or_none

        if self.http_method:
            type_method = f'HTTP request: {styled_http_method(self.http_method)}'
        else:
            type_method = f'WEBSOCKET request: {self.ws_verb}'
        if request is not None:
            path = request.path
            token_auth = request.token_auth
            user = user_or_none(request.user)
        else:
            assert scope is not None
            path = scope.get('path') or ''
            token_auth = scope.get('token_auth')
            user = user_or_none(scope.get('user'))

        operation_name = (path or 'unknown').strip('/').replace('/', '.')

        auth_method: str
        if user:
            if token_auth is not None and token_auth.token_type:
                auth_method = token_auth.token_type
            else:
                auth_method = 'session'
        else:
            auth_method = 'anonymous'

        log = logger.bind(**self.get_full_log_context(), **{'auth.method': auth_method})
        log.info(f'{type_method} {path}')
        start_ts = time.time()
        with ExitStack() as stack:
            _rich_traceback_omit = True
            if env_bool('PROFILE_REQUESTS', default=False):
                self._enter_viztracer_stack(stack, operation_name)
            stack.enter_context(self.contextualize_logger())
            sentry_scope = stack.enter_context(self.with_sentry_context())
            yield sentry_scope
        end_ts = time.time()
        log.info('Request completed in %.1f ms' % ((end_ts - start_ts) * 1000))
